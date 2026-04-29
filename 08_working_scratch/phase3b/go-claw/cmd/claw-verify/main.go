// claw-verify reads a pilot OCR JSON file and writes a catchword + marginal
// verification report to disk.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"github.com/paulboys/ussher-in/go-claw/internal/catchword"
	"github.com/paulboys/ussher-in/go-claw/internal/marginal"
	"github.com/paulboys/ussher-in/go-claw/internal/pilot"
)

type combinedReport struct {
	Catchword  catchword.Report     `json:"catchword"`
	Marginalia []marginal.Reference `json:"marginalia"`
}

func main() {
	pilotPath := flag.String("pilot", "", "path to part_pilot_ocr.json")
	reportPath := flag.String("report", "", "path to write the verification report (JSON)")
	flag.Parse()

	if *pilotPath == "" || *reportPath == "" {
		fmt.Fprintln(os.Stderr, "usage: claw-verify --pilot <path> --report <path>")
		os.Exit(2)
	}

	pages, err := pilot.Load(*pilotPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	report := combinedReport{
		Catchword:  catchword.Verify(pages),
		Marginalia: marginal.Extract(pages),
	}

	if err := os.MkdirAll(filepath.Dir(*reportPath), 0o755); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	data, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := os.WriteFile(*reportPath, data, 0o644); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Printf(
		"Verified %d page-pairs: match=%d mismatch=%d missing=%d (marginalia: %d) -> %s\n",
		report.Catchword.Total,
		report.Catchword.Match,
		report.Catchword.Mismatch,
		report.Catchword.Missing,
		len(report.Marginalia),
		*reportPath,
	)
}
