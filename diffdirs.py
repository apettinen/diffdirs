#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=C0103, C0301, C0325
"""
Tool to check differences in files between two directories. Suitable for e.g.
checking if update has changed something. Goes through directory listings
(relative paths) and does comparison of files with same paths via filecmp.cmp or alternatively by sha256 hash.

Antti Pettinen (@apettinen)

Copyright: 
2018 Antti Pettinen
2017 Tampere University of Technology

License: Apache 2.0
"""
#from __future__ import print_function
import os
import sys
import argparse
import filecmp
from json import dump as jdump
from hashlib import sha256

class comparisonException(Exception):
    """Raise this when error"""

class dirInfo(object):
    """
    Directory to analyze as an object. Contains a list of files in directory (recursive) and a dictionary of fileInfo object of each file
    """

    def __init__(self, dirpath, blocksize=65536, skip_files_list=None):
        """Return dirInfo object"""
        self.dirpath = dirpath
        self.blocksize = blocksize
        self.files_in_dir = self.get_files_in_dir()
        # we initialize the dict of hashes empty
        self.file_infos = {}
        self.dict_of_hashes = {}
        self.skip_files_list = skip_files_list

    def get_files_in_dir(self):
        '''wrapper for os.walk and os.path to get the relative paths of files'''
        files_in_dir = []
        try:
            for root, _dirs, files in os.walk(self.dirpath):
                for current_file in files:
                    files_in_dir.append(os.path.relpath(os.path.join(root, current_file), self.dirpath))
        except Exception as cex:
            raise comparisonException(cex)
        return files_in_dir

    def generate_fileInfo_objects(self):
        """Generate fileInfo objects for files in directory structure"""
        if not self.skip_files_list:
            self.skip_files_list = []
        for file_in_dir in self.files_in_dir:
            if file_in_dir not in self.skip_files_list:
                self.file_infos[file_in_dir] = fileInfo(os.path.join(self.dirpath, file_in_dir), self.blocksize)
        return self.file_infos

    def generate_hashes(self):
        """Generate hashes for all files in directory structure, returning a dict of relative file name and its hash"""
        if not self.skip_files_list:
            self.skip_files_list = []
        if not self.file_infos:
            self.generate_fileInfo_objects()
        for fi in self.file_infos:
            if os.path.isfile(self.file_infos[fi].filepath):
                self.dict_of_hashes[fi] = self.file_infos[fi].get_sha256_hash()
        return self.dict_of_hashes

class fileInfo(object):
    """File object containing information, such as sha256 hash and stat. sha256 hash is not generated during init, but can be generated and stored in the object later"""
    def __init__(self, filepath, blocksize=65536):
        self.filepath = filepath
        self.blocksize = blocksize
        #self.hash = self.get_sha256_hash(self.filepath)
        self.hash = ""
        self.stat = self.get_posix_stat()

    def get_sha256_hash(self):
        '''Compute SHA256 hash of a file, with configurable blocksize (defaults to 65536)'''
        #sha256hasher = sha256()
        # don't compute the hash again:
        if not self.hash:
            try:
                sha256hasher = sha256()
                with open(self.filepath, 'rb') as f_d:
                    buf = f_d.read(self.blocksize)
                    while len(buf) > 0:
                        sha256hasher.update(buf)
                        buf = f_d.read(self.blocksize)
                    self.hash = sha256hasher.hexdigest()
            except IOError as ierr:
                raise comparisonException(ierr)
        return self.hash

    def get_posix_stat(self):
        '''Get POSIX stat of file'''
        if os.path.isfile(self.filepath):
            return os.stat(self.filepath)
        else:
            return None

def compare_directories(orig_dir_files, new_dir_files):
    '''Compare the contents of two directories to see what file names exist only in the orig_dir or new_dir or file names that exist in new_dir and orig_dir.'''
    try:
        orig_only_files = [orig_file for orig_file in orig_dir_files if orig_file not in new_dir_files]
        new_files = [new_file for new_file in new_dir_files if new_file not in orig_dir_files]
        common_files = [common_file for common_file in new_dir_files if common_file in orig_dir_files]
    except Exception as cex:
        raise comparisonException(cex)
    return orig_only_files, new_files, common_files

def compare_files(orig_file_infos, new_file_infos, files_to_compare, type_of_comparison="stat"):
    """Wrapper for _compare_fileinfos, i.e. compare fileInfo objects"""
    changed = []
    unchanged = []
    for file_to_cmp in files_to_compare:
        try:
            if _compare_fileinfos(orig_file_infos[file_to_cmp], new_file_infos[file_to_cmp], type_of_comparison):
                unchanged.append(file_to_cmp)
            else:
                changed.append(file_to_cmp)
        except comparisonException as ex:
            raise comparisonException("Comparing {0} and {1} failed with error: {2}".format(orig_file_infos[file_to_cmp], new_file_infos[file_to_cmp], ex))
    return changed, unchanged


def _compare_fileinfos(orig_file_info, new_file_info, type_of_comparison, shallow=False):
    """
    Compare files using filecmp.cmp (shallow or not [default]) or by hash, returns True if the files are the same (as deemed by the comparison operation).
    @input fileInfo object
    """
    if not isinstance(orig_file_info, fileInfo) or not isinstance(new_file_info, fileInfo):
        raise comparisonException("Trying to compare non-fileInfo objects")

    if type_of_comparison == "stat":
        try:
            same_file = filecmp.cmp(orig_file_info.filepath, new_file_info.filepath, shallow)
        except OSError as oerr:
            raise comparisonException("{0}{1}".format(oerr.errno, oerr.message))
    elif type_of_comparison == "hash":
        try:
            same_file = bool(str(orig_file_info.get_sha256_hash()) == str(new_file_info.get_sha256_hash()))
        except OSError as oerr:
            raise comparisonException("{0}{1}".format(oerr.errno, oerr.message))
    else:
        raise comparisonException("Possibly unknown comparison type {0}?".format(type_of_comparison))
    return same_file

def compare_full_dirs(orig_dir_obj, new_dir_obj):
    """Compare every file in the two directories by hashes"""
    # generate hashes for all files and store into object
    print("Computing sha256 hashes for full directories can take a long time!")
    print("Computing sha256 hashes for {0}...".format(orig_dir_obj.dirpath))
    orig_dir_obj.generate_hashes()
    print("Computing sha256 hashes for {0}...".format(new_dir_obj.dirpath))
    new_dir_obj.generate_hashes()
    print("Computing differences via sha256 hashes...")
    common_hashes = set(orig_dir_obj.dict_of_hashes.values()) & set(orig_dir_obj.dict_of_hashes.values())

    hash_map = {}
    unchanged = []
    for ch in common_hashes:
        found_in_orig = [k for k, v in orig_dir_obj.dict_of_hashes.iteritems() if v == ch]
        found_in_new = [k for k, v in new_dir_obj.dict_of_hashes.iteritems() if v == ch]
        # intersection of the two lists above is the unchanged files
        unchanged.extend(list(set(found_in_orig).intersection(found_in_new)))
        # dictionary containing hash and the corresponding files in both
        # directories
        hash_map[ch] = {\
                        orig_dir_obj.dirpath: found_in_orig,\
                        new_dir_obj.dirpath: found_in_new\
                        }
    # we have now found the common files by sha256 hash. All other files can
    # be considered as changed or new
    changed_or_new = list(set(new_dir_obj.files_in_dir).symmetric_difference(unchanged))
    return changed_or_new, unchanged, hash_map

def write_to_JSON(result, outfile):
    """Write parsed query result (a Python dict) to JSON file"""
    try:
        with open(outfile, 'w') as json_file:
            jdump(result, json_file, indent=2, sort_keys=False, separators=(',', ':'), ensure_ascii=False)
    except IOError as err:
        raise comparisonException('Writing JSON output to {of} failed with error {ec}.'.format(of=outfile, ec=err))

def main(orig_dir, new_dir, blocksize, comparison_operator):
    """ main source of pain """
    if not os.path.isdir(orig_dir):
        raise comparisonException("Directory {d} does not exist".format(d=orig_dir))
    if not os.path.isdir(new_dir):
        raise comparisonException("Directory {d} does not exist".format(d=new_dir))

    changed_files = []
    unchanged_files = []
    print("Initializing comparison, this might take a while...")
    # dirInfo objects:
    print("Listing files in {0}".format(orig_dir))
    orig_dir_obj = dirInfo(orig_dir, blocksize)
    print("Listing files in {0}".format(new_dir))
    new_dir_obj = dirInfo(new_dir, blocksize)
    # fileInfo objects:
    print("Generating information of files in {0}".format(orig_dir))
    orig_dir_file_objs = orig_dir_obj.generate_fileInfo_objects()
    print("Generating information of files in {0}".format(new_dir))
    new_dir_file_objs = new_dir_obj.generate_fileInfo_objects()
    print("Comparing the contents of {od} and {nd}".format(od=orig_dir, nd=new_dir))
    orig_files, new_files, common_files = compare_directories(orig_dir_obj.get_files_in_dir(), new_dir_obj.get_files_in_dir())

    if comparison_operator == "sha256":
        print("Checking differences between ALL files in both directories via sha256 hashes... This might take a while!")
        #print("Comparing common files by their hashes...")
        # compare existing files by their hashes:
        changed_files, unchanged_files, hashmapping = compare_full_dirs(orig_dir_obj, new_dir_obj)
    elif comparison_operator == "common_only":
        print("Comparing common files by their sha256 hashes")
        #changed_files, unchanged_files = _compare_files(orig)
        changed_files, unchanged_files = compare_files(orig_dir_file_objs, new_dir_file_objs, common_files, "hash")
        hashmapping = None
    elif comparison_operator == "filecmp":
        print("Comparing common files via filecmp.cmp")
        changed_files, unchanged_files = compare_files(orig_dir_file_objs, new_dir_file_objs, common_files, "stat")
        hashmapping = None
    else:
        raise comparisonException("Unknown comparison operator: {0}".format(comparison_operator))

    return orig_files, new_files, common_files, changed_files, unchanged_files, hashmapping

if __name__ == "__main__":
    """
    Compare files in directories and print out new files and
    files that have changed (based on sha256 hash)
    """
    parser = argparse.ArgumentParser(prog='whatsnewinmacos.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    comparison_operator_group = parser.add_mutually_exclusive_group()
    # optional arguments
    parser.add_argument('-o', '--path-to-original', help='Path to directory containing original files (e.g. older OS version)', type=str, dest='orig_dir')
    parser.add_argument('-n', '--path-to-new', help='Path to directory containing new files (e.g. newer OS version)', type=str, dest='new_dir')
    parser.add_argument('-b', '--blocksize', help="Blocksize for sha256", type=int, default=65536, dest='blocksize')
    parser.add_argument('-s', '--save-output', help='Save output to a JSON file', type=str, dest='outfile')
    parser.add_argument('-v', '--verbose', action='count', help='Print output', dest='verbosity')
    comparison_operator_group.add_argument("-filecmp", action="store_const", dest="comparison_operator", help="Compare using filecmp only", const="filecmp", default="filecmp")
    comparison_operator_group.add_argument("-common", action="store_const", dest="comparison_operator", help="Compare using filecmp and use sha256 has for common files", const="common_only")
    comparison_operator_group.add_argument("-sha256", action="store_const", dest="comparison_operator", help="Compare by sha256 only", const="sha256")
    args = parser.parse_args()

    if not args.verbosity and not args.outfile:
        print("No output defined, you might want to see something too?")
        sys.exit(1)

    try:
        only_in_orig, are_new, are_common, have_changed, are_unchanged, hashmap = main(args.orig_dir, args.new_dir, args.blocksize, args.comparison_operator)
    except comparisonException as ex:
        print("Comparison failed with error: {e}".format(e=ex))
        sys.exit(1)

    if args.verbosity:
        if only_in_orig:
            print("---------------")
            print("The following files are only in {nd}:".format(nd=args.orig_dir))
            print("---------------")
            print("\n".join(only_in_orig))
        if are_new:
            print("---------------")
            print("The following files are new in {nd}:".format(nd=args.new_dir))
            print("---------------")
            print("\n".join(are_new))
        else:
            print("---------------")
            print("No new files in {nd}:".format(nd=args.new_dir))
            print("---------------")
        if are_common:
            print("---------------")
            print("The following files exist in both in {od} and {nd} :".format(od=args.orig_dir, nd=args.new_dir))
            print("---------------")
            print("\n".join(are_common))
            print("---------------")
            print("These files are different between {od} and {nd}:".format(od=args.orig_dir, nd=args.new_dir))
            print("---------------")
            print("\n".join(have_changed))
            #print changed_files
            print("---------------")
            print("These files are same between {od} and {nd}:".format(od=args.orig_dir, nd=args.new_dir))
            print("---------------")
            print("\n".join(are_unchanged))
            print("---------------")
        else:
            print("---------------")
            print("No files with the same name in both {od} and {nd} :".format(od=args.orig_dir, nd=args.new_dir))
            print("---------------")
    if args.outfile:
        try:
            print("Saving results to {sf}...".format(sf=args.outfile))
            if hashmap:
                result_dict = {"directories":[args.new_dir, args.orig_dir], "new_files":are_new, "common_files":are_common, "have_changed":have_changed, "unchanged":are_unchanged, "mapping_by_hashes":hashmap}
            else:
                result_dict = {"directories":[args.new_dir, args.orig_dir], "new_files":are_new, "common_files":are_common, "have_changed":have_changed, "unchanged":are_unchanged}
            write_to_JSON(result_dict, args.outfile)
            print("Results saved.")
        except comparisonException as cex:
            print("Saving file failed with error:{cx}".format(cx=cex))
            sys.exit(1)
    sys.exit(0)
