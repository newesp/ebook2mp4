# OCR runtime and models

Tesseract Windows 5.4.0.20240606 is built by UB Mannheim:
https://github.com/UB-Mannheim/tesseract/releases/tag/v5.4.0.20240606
The unmodified installer is extracted at build time; it is never executed.
Archive SHA-256: c885fff6998e0608ba4bb8ab51436e1c6775c2bafc2559a19b423e18678b60c9.
Tesseract AUTHORS, LICENSE and README are in doc/. Upstream source:
https://github.com/UB-Mannheim/tesseract/tree/v5.4.0.20240606

Runtime DLLs come from that same archive. They include Tesseract, Leptonica,
libarchive, libb2, bzip2, OpenSSL, libdeflate, Expat, GCC runtimes,
giflib, libiconv, JBIG-KIT, libjpeg-turbo, LERC, LZ4, XZ, OpenJPEG,
libpng, libtiff, libwebp, mingw-w64 winpthreads, Zstandard and zlib.
MSYS2 package recipes, source references and license declarations:
https://github.com/msys2/MINGW-packages
JBIG-KIT is GPL licensed; libiconv and some runtime components have LGPL/GPL
terms with runtime exceptions where applicable. Do not describe the entire
runtime as Apache-2.0. T23 must complete installer redistribution/source-offer
and dependency-license verification before public installer delivery.

Language data: tesseract-ocr/tessdata_fast 4.1.0, commit
65727574dfcd264acbb0c3e07860e4e9e9b22185, Apache License 2.0.
https://github.com/tesseract-ocr/tessdata_fast/tree/65727574dfcd264acbb0c3e07860e4e9e9b22185
Models are downloaded only on user action. The application verifies pinned
sizes and SHA-256 hashes. The Apache-2.0 text included in doc/LICENSE also
applies to the models. No PDF page or manuscript is uploaded by OCR.
