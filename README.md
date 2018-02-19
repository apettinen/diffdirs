### diffdirs 
This imaginatively named tool can be used for comparison of the contents of two directory structures.

I made this for strictly my own purposes, but if you find bugs/improvements,
please feel free to make a pull requesti. You can fork/use this as you wish.

Checks the following:
- what files are new
- what files exist in both directories:
  - have the files changed...
  - or are they the same files

Uses ```filecmp``` and/or sha256 hashes to determine if file has been changed.

Outputs either XML or JSON.

MIT License

Copyright (c) 2018 Antti Pettinen
