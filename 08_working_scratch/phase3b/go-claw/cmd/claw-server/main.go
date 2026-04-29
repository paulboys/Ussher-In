// claw-server runs a small read-only HTTP API for side-by-side verification.
// It deliberately binds to a non-5000 port to coexist with the Python Flask
// annotation UI.
package main

import (
	"flag"
	"fmt"
	"net/http"
	"os"

	"github.com/paulboys/ussher-in/go-claw/internal/pilot"
	"github.com/paulboys/ussher-in/go-claw/internal/server"
)

func main() {
	pilotPath := flag.String("pilot", "", "path to part_pilot_ocr.json")
	port := flag.Int("port", 5050, "port to bind (must not be 5000)")
	host := flag.String("host", "127.0.0.1", "host to bind")
	flag.Parse()

	if *pilotPath == "" {
		fmt.Fprintln(os.Stderr, "usage: claw-server --pilot <path> [--port 5050]")
		os.Exit(2)
	}
	if *port == 5000 {
		fmt.Fprintln(os.Stderr, "claw-server refuses to bind port 5000 (reserved for the Flask annotation UI)")
		os.Exit(2)
	}

	pages, err := pilot.Load(*pilotPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	store := server.NewStore(pages)
	addr := fmt.Sprintf("%s:%d", *host, *port)
	fmt.Printf("claw-server listening on http://%s/ (read-only)\n", addr)
	if err := http.ListenAndServe(addr, store.Mux()); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
