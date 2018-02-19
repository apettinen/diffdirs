### diffdirs 
This imaginatively named tool can be used for comparison of the contents of two directory structures.
Suitable for e.g. checking if update has changed something. Goes through directory listings
(relative paths) and does comparison of files with same paths via filecmp.cmp or alternatively by sha256 hash.

I made this for strictly my own purposes, but if you find bugs/improvements,
please feel free to make a pull requesti. You can fork/use this as you wish.

Checks the following:
- what files are new
- what files exist in both directories:
  - have the files changed...
  - or are they the same files

As mentioned, the tools uses ```filecmp``` and/or sha256 hashes to determine if file has been changed.

Outputs either XML or JSON.

#### Usage:

```whatsnewinmacos.py [-h] [-o ORIG_DIR] [-n NEW_DIR] [-b BLOCKSIZE] [-s OUTFILE] [-v] [-filecmp | -common | -sha256]```

License: Apache 2.0

Copyright (c) 2018 Antti Pettinen, 2017 Tampere University of Technology
