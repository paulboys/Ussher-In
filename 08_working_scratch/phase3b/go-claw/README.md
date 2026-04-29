# Claw — Go Verification Layer for Ussher-In

`claw` is a small Go module that complements the Python OCR/annotation
pipeline with deterministic verification commands and a side-by-side
review server. It is inspired by SciClaw conventions: `cmd/` for binaries,
`internal/` for shared logic, plus a Makefile for build ergonomics.

## Layout

```
go-claw/
  cmd/
    claw-verify/    # verifies catchwords + marginal references against pilot OCR JSON
    claw-server/    # local side-by-side verification HTTP server (non-port-5000)
  internal/
    pilot/          # parses pilot_ocr.json records produced by the Python pipeline
    catchword/      # catchword vs first-token-of-next-page comparison (concurrent)
    marginal/       # marginal reference / scripture citation extraction
    server/         # HTTP handlers for the verification server
  Makefile
  go.mod
```

## Build

```powershell
cd 08_working_scratch/phase3b/go-claw
make build           # builds claw-verify and claw-server into ./bin/
```

## Verify a part

```powershell
./bin/claw-verify --pilot ../../../01_raw_ocr_output/part1/part1_pilot_ocr.json `
                  --report ./reports/part1_catchword.json
```

The verification report JSON is machine-readable and lists per-page
catchword status (`match`, `mismatch`, `missing`) plus extracted marginal
references suitable for indexing into research JSON outputs.

## Side-by-side server

```powershell
./bin/claw-server --pilot ../../../01_raw_ocr_output/part1/part1_pilot_ocr.json `
                  --port 5050
```

Then open <http://127.0.0.1:5050/>. The server is read-only with respect
to annotation JSON; it never writes to `08_working_scratch/phase3b/annotations/`,
so the Flask annotation UI on port 5000 remains the single writer.
