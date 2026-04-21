"""Check ligature handling: lat vs lat+grc."""
for p in [33, 34, 35]:
    l = open(f"08_working_scratch/test_lat_grc_p{p:04d}_lat.txt", encoding="utf-8").read()
    g = open(f"08_working_scratch/test_lat_grc_p{p:04d}_lat_grc.txt", encoding="utf-8").read()
    ae = chr(0xe6)
    print(f"Page {p}:")
    print(f"  ae ligature: lat={l.count(ae)}  grc={g.count(ae)}")
    print(f"  'quz' (should be quæ): lat={l.count('quz')}  grc={g.count('quz')}")
    print(f"  'czc' (should be cæc): lat={l.count('czc')}  grc={g.count('czc')}")
    print(f"  ':&' (mangled æ):      lat={l.count(':&')}  grc={g.count(':&')}")
    print(f"  'prz' (should be præ): lat={l.count('prz')}  grc={g.count('prz')}")
    # Show lines with these patterns
    for i, (ll, gl) in enumerate(zip(l.splitlines(), g.splitlines())):
        if ll != gl and ae not in gl and 'quz' not in gl:
            continue
        if ae in ll or ae in gl or 'quz' in ll or ':&' in ll:
            print(f"  L{i}: LAT:     {ll.strip()}")
            print(f"  L{i}: LAT+GRC: {gl.strip()}")
