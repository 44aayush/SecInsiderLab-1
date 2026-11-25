# Lab 1 — Networking Basics, Monitoring Tools, Network Attacks and Defense, and Machine Learning

Security Insider Lab I, group G8. This lab is research and measurement work, so there is no run script.

Task spec: [lab-1.pdf](lab-1.pdf). Report: [G8_Report1_source/thesis.pdf](G8_Report1_source/thesis.pdf). Slides: [Lab1_Security_Insider_Group8_edited.pptx](Lab1_Security_Insider_Group8_edited.pptx).

## Topics

1. **Networking basics:** the TCP/IP stack, core protocols, BGP, ISPs, IXPs and DE-CIX.
2. **Monitoring tools:** Wireshark captures of ICMP ping, DNS, the TCP three-way handshake, encapsulation with HTTP, and HTTPS/TLS.
3. **Network attacks and defense:** five attack types, DDoS (types, reflection and amplification, trends), infrastructure defenses, attack tools (described from the literature, none run), and defense tools such as Cloudflare and eBPF/XDP.
4. **Machine learning:** why ML helps detect attacks, algorithms for DDoS detection, evaluation, data and challenges.

## Build the report

The LaTeX source is in [G8_Report1_source/](G8_Report1_source/) (chapters in `chapters/`):

```bash
cd G8_Report1_source
latexmk -r latexmkrc_2 thesis.tex   # LuaLaTeX + Biber; removes temporary files afterwards
```
