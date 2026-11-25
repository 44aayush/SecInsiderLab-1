# SecInsiderLab-1

Course: Security Insider Lab I, University of Passau, WiSe 26/27. Group G8.

The labs build on each other. Lab 1 covers networking basics, monitoring tools and the main network attacks and defenses. Lab 2 uses machine learning to detect network attacks on the CICIDS2017 dataset. Lab 3 trains and compares classical ML and deep learning models for DDoS detection and adds in-kernel XDP mitigation (a source-IP blocklist and a rate limiter).

| Lab | Title | Description | README | Task spec |
|---|---|---|---|---|
| 1 | Networking Basics, Monitoring Tools, Network Attacks and Defense, and Machine Learning | Research and Wireshark measurements, attack and defense survey | [Lab1/README.md](Lab1/README.md) | [Lab1/lab-1.pdf](Lab1/lab-1.pdf) |
| 2 | Machine Learning for Network Attack Detection | Pipelines on CICIDS2017 (Friday DDoS) | [Lab2/README.md](Lab2/README.md) | [Lab2/lab-2.pptx](Lab2/lab-2.pptx) |
| 3 | Training ML and DL models for DDoS detection | 5 classical and 3 neural models compared; XDP blocklist and rate limiter | [Lab3/README.md](Lab3/README.md) | [Lab3/Security_Insider_lab_3.pptx](Lab3/Security_Insider_lab_3.pptx) |

## Quick start

```bash
git clone https://github.com/44aayush/SecInsiderLab-1.git && cd SecInsiderLab-1
git lfs pull
bash Lab2/run.sh
bash Lab3/run.sh --quick
```

## Requirements

- Linux, [uv](https://docs.astral.sh/uv/), git-lfs
- Lab 3 XDP extras: clang, llvm, libbpf-dev, gcc-multilib, bpftool, iproute2 (attaching needs sudo)

## License

See [LICENSE](LICENSE).
