# Document and media reading

The Vision tools run locally through Central Mind and the configured Ollama
vision model (`qwen3-vl:8b`). They do not send source files to an external API.

`document_read` reads UTF-8 text, PDF, DOCX, PPTX, XLSX, and common image
formats, including screenshots. PDF pages with little or no embedded text are
rendered and OCRed. Images embedded in DOCX and PPTX files are OCRed too.
Image reading returns both visible-text transcription and a visual description.

`video_read` samples every frame at the requested `fps` (one frame per second
by default), then transcribes visible screen text and describes each sampled
frame. It does not impose a frame-count cap. It analyzes visual content only;
it does not transcribe audio. Temporary video files and extracted frames are
removed when processing finishes.

Memory Intake accepts these formats directly. Binary uploads are passed to
the reader as data and are not saved into the workspace. Extracted text remains
unverified Raw Memory until the Trainer reviews and submits it.

The app runtime installs the Python readers and bundled FFmpeg from
`requirements-runtime.txt`. OCR and visual descriptions require the configured
Ollama vision model to be available locally.
