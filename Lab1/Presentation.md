# Lab 1 Presentation: My Part (Aayush Kapoor)

**Security Insider Lab I, Group 8**
**My tasks:** Task 1, Networking Basics (Introduction) and Task 3, Network Attacks and Defense
**Speaking time:** about 7 minutes (~900 words at ~130 words per minute)
**Matching slides:** "TCP/IP Stack and Core Protocols", "BGP, IXPs and DE-CIX", "Network Attacks and DDoS", "Attack Tools and Defenses", "Summary and Limitations"

> Times are cumulative. The bullets are what I say. *Italic lines* are things to point at on the slide.

---

## 0. Opening (0:00 to 0:20)

- In this lab I did two parts: **Task 1, the networking basics**, and **Task 3, network attacks and defense**.
- Task 1 explains how the Internet works. Task 3 explains how attackers abuse that design and how we defend against it. The two connect, and I will point out where.

---

## 1. TCP/IP Stack and Core Protocols (0:20 to 1:30)

- The Internet runs on the **four-layer TCP/IP stack**: Application, Transport, Internet and Link. Each layer answers one question:
  - Application: *what is being said?* (HTTP, DNS, TLS)
  - Transport: *which program gets it?* (TCP, UDP, using ports)
  - Internet: *which machine, which route?* (IP, ICMP, using IP addresses)
  - Link: *how do we cross this one hop?* (Ethernet, Wi-Fi, using MAC addresses)
- **Encapsulation:** each layer wraps the data in its own header, like a letter inside an envelope inside a postman's bag. A router unwraps only up to the IP layer, because the destination IP is all it needs.
  - *Point at:* our first captured SYN was 14 B Ethernet + 40 B IPv6 + 40 B TCP = **94 bytes**.
- The key protocols:
  - **IP** delivers on a best-effort basis and **does not verify the source address**. This is what makes IP spoofing possible, and spoofing comes back in Task 3.
  - **TCP** is reliable and ordered and starts with the **three-way handshake** (SYN, SYN-ACK, ACK). The handshake only synchronises sequence numbers. It does not check who you are.
  - **UDP** has no handshake and very little overhead. Video calls use it; banking uses TCP.
  - **DNS** turns names into IPs (A records for IPv4, AAAA for IPv6). **HTTPS** is HTTP inside **TLS**, which is why plain HTTP is readable in a capture and HTTPS is not.

---

## 2. BGP, IXPs and DE-CIX (1:30 to 3:00)

- The Internet is tens of thousands of independent networks called **autonomous systems**. **BGP** is how they announce which IP prefixes they can reach. My analogy: airlines sharing route maps. If a network stops announcing its routes, it disappears from the map.
- **BGP's trust problem:** announcements are believed unless filtered, which allows **hijacks** and **route leaks**. The main fix is **RPKI**: the owner signs which AS may announce a prefix.
- **Case study, the Facebook outage of 4 October 2021.** No attacker was involved:
  1. A maintenance command cut the links between Facebook's data centers.
  2. As a safety rule, the DNS servers withdrew their own BGP routes.
  3. facebook.com stopped resolving worldwide.
  4. The repair tools ran on the same network, so engineers had to go on site. Services were down for about **six hours**.
  - Lesson: **BGP and DNS together decide whether a service can be found at all**, however many servers are running.
- **ISP vs. IXP:** an ISP sells Internet access. An **IXP** is a facility where many networks connect to one switch and **peer** directly. That is cheaper and faster, keeps local traffic local and adds redundancy.
- **DE-CIX Frankfurt:** founded **1995** by three ISPs in the back room of an old post office. Today it runs **60+ exchanges**, has **~1,100 networks** in Frankfurt, and set a **21.47 Tbit/s record in October 2026**, more than 160 % above early 2020. These are press figures and change almost every month.

---

## 3. Five Network Attacks (3:00 to 4:00)

- First, a disclaimer: **Task 3 is based on literature and vendor reports only. We did not run any attack tool**, because using them against systems you don't own can be a crime in Germany (§ 303b StGB).
- I chose five attacks that hit **different layers**:
  - **DDoS:** many machines flood a target (a crowd blocking a shop door). Defense: rate limiting, scrubbing, anycast.
  - **Man-in-the-middle:** an attacker relays and changes traffic (a postman who opens letters). Defense: TLS with certificate checks, VPN.
  - **ARP spoofing:** fake ARP replies make victims send frames to the attacker's MAC. Defense: dynamic ARP inspection.
  - **DNS spoofing:** forged answers point a name to the attacker's IP (a wrong phone-book entry). Defense: DNSSEC.
  - **Port scanning:** probing for open ports, usually reconnaissance before an attack. Defense: firewall, IDS.

---

## 4. DDoS in Depth (4:00 to 5:00)

- **Three families**, by the resource they exhaust:
  - **Volumetric:** bandwidth, measured in bit/s (UDP floods, amplification).
  - **Protocol:** server state, measured in packets/s (SYN flood).
  - **Application layer:** the application itself, measured in requests/s (HTTP floods, Slowloris).
- **The SYN flood links back to Task 1:** the server reserves memory for every half-open connection. With spoofed SYNs the final ACK never comes, the table fills up and real users are refused. The countermeasure is **SYN cookies**: no state is kept until the handshake completes.
- **Reflection and amplification** exploit UDP's missing handshake: the attacker spoofs the victim's address, and a server sends a much larger reply to the victim. CISA lists amplification factors of 28 to 54 for DNS, **~557 for NTP**, and up to 51,000 for memcached.
- **Scale:** Cloudflare reported **47.1 million attacks in 2025 (+121 %)**, and a peak of **31.4 Tbit/s that lasted only 35 seconds**. Bursts that short cannot be handled by hand, which is why detection has to be automated.
- **Infrastructure defenses are layered:** rate limiting, ACLs, load balancing, anycast/CDN, scrubbing centers, blackholing (RTBH), anti-spoofing (BCP 38), SYN cookies and over-provisioning. Several of these tie back to Task 1: anycast is a BGP technique, and blackholing is often done at an IXP such as DE-CIX.

---

## 5. Attack Tools and the Two Defenses (5:00 to 6:20)

- **Five tools, from old to new:**
  - **LOIC:** simple GUI flooder used by Anonymous around 2010. It does not hide the user, so participants were traced.
  - **Slowloris:** sends HTTP headers very slowly and ties up server connections with almost no bandwidth.
  - **hping3:** crafts custom packets. It is dual-use, since it is also a legitimate firewall test tool.
  - **Mirai (2016):** IoT botnet using default passwords. It took down the DNS provider Dyn.
  - **Aisuru / Kimwolf:** millions of IoT devices and Android TV boxes, behind the **2025 records**.
  - **The trend:** attackers went from volunteers to hijacked devices. Attack size is now limited by the number of insecure devices on the Internet, not by the attacker's own resources.
- **Two defenses that work in very different places:**
  - **Cloudflare** protects at the network edge. BGP anycast spreads the attack over many data centers. XDP programs (L4Drop) drop known attack traffic, and the `dosd` service creates new mitigation rules within seconds. It stopped the 31.4 Tbit/s attack **with no human involved**. Weaknesses: you depend on a third party, it costs money, you have to trust the provider (it terminates TLS), and attackers can bypass it if the origin IP leaks.
  - **eBPF/XDP** protects a single Linux host. Verified programs run in the network driver and drop packets *before* the kernel stack processes them (a bouncer at the door). It is very fast and gives full control, but it needs expertise and **cannot help when the incoming link itself is full**.
  - **They complement each other:** Cloudflare handles volumetric floods, and XDP handles protocol floods that reach the host.

---

## 6. Summary and Limitations (6:20 to 7:00)

- **Takeaways from my part:**
  - The Internet's core protocols were built on trust. IP doesn't verify sources, BGP believes announcements, and ARP and DNS have no authentication. Every attack I covered exploits one of these.
  - A SYN flood abuses the TCP handshake, and UDP makes spoofing and amplification possible.
  - No single defense is enough. Edge protection (Cloudflare) and host protection (XDP) complement each other, and machine learning, my teammate's part, provides the automated detection.
- **Limitations:** the attack figures come from vendor and press reports, and no attack tool was run.
- Thank you. I'm happy to take questions.

---

## Glossary: Abbreviations and Terms

| Term | Meaning |
|---|---|
| **TCP/IP** | Transmission Control Protocol / Internet Protocol: the four-layer model the Internet runs on |
| **OSI** | Open Systems Interconnection: the seven-layer teaching model |
| **IP** | Internet Protocol: addressing and best-effort packet delivery |
| **IPv4 / IPv6** | IP version 4 (32-bit addresses) / version 6 (128-bit addresses) |
| **ICMP / ICMPv6** | Internet Control Message Protocol: diagnostics and errors (ping, traceroute) |
| **TCP** | Transmission Control Protocol: reliable, ordered byte stream |
| **UDP** | User Datagram Protocol: connectionless, no handshake, low overhead |
| **SYN / SYN-ACK / ACK** | Synchronize / Synchronize-Acknowledge / Acknowledge: the three TCP handshake packets |
| **TTL / Hop limit** | Time To Live (IPv4) / Hop Limit (IPv6): a counter each router decrements; at 0 the packet is dropped |
| **MAC** | Media Access Control address: hardware address used on the link layer |
| **DNS** | Domain Name System: translates names to IP addresses |
| **A / AAAA record** | DNS record types for an IPv4 / IPv6 address |
| **HTTP / HTTPS** | Hypertext Transfer Protocol / HTTP Secure (HTTP inside TLS) |
| **TLS** | Transport Layer Security: encryption, integrity and server authentication |
| **SNI** | Server Name Indication: the hostname sent unencrypted in the TLS Client Hello |
| **BGP** | Border Gateway Protocol: routing between autonomous systems |
| **AS** | Autonomous System: an independently operated network with its own AS number |
| **Prefix** | A block of IP addresses, e.g. 192.0.2.0/24 |
| **Hijack / Route leak** | Announcing address space you don't own / passing on routes you shouldn't |
| **RPKI** | Resource Public Key Infrastructure: signed statements of which AS may originate a prefix |
| **ISP** | Internet Service Provider (e.g. Deutsche Telekom, Vodafone) |
| **IXP** | Internet Exchange Point: facility where networks peer directly |
| **Peering** | Two networks exchanging traffic directly instead of through a paid transit provider |
| **DE-CIX** | Deutscher Commercial Internet Exchange: Frankfurt-based IXP operator |
| **Tbit/s** | Terabits per second (10^12 bits/s) |
| **DoS / DDoS** | Denial of Service / Distributed Denial of Service |
| **Botnet** | Network of compromised devices controlled by an attacker |
| **C2** | Command-and-Control server that sends orders to a botnet |
| **MitM** | Man-in-the-Middle attack |
| **ARP** | Address Resolution Protocol: maps IPv4 addresses to MAC addresses |
| **DAI** | Dynamic ARP Inspection: switch feature that blocks forged ARP replies |
| **DNSSEC** | DNS Security Extensions: digital signatures on DNS answers |
| **VPN** | Virtual Private Network: encrypted tunnel |
| **IDS** | Intrusion Detection System |
| **Nmap** | Network Mapper: the best-known port scanner |
| **SYN flood** | Flood of SYN packets that fills the server's half-open connection table |
| **SYN cookies** | Server encodes connection state in the sequence number and stores nothing until the handshake completes |
| **Reflection / Amplification** | Spoofed requests make third-party servers send (much larger) replies to the victim |
| **NTP** | Network Time Protocol (amplification factor ~557) |
| **memcached** | In-memory caching server (amplification factor up to ~51,000) |
| **Slowloris** | Tool that holds server connections open by sending headers very slowly |
| **LOIC** | Low Orbit Ion Cannon: GUI flooding tool |
| **hping3** | Command-line packet-crafting tool |
| **Mirai** | 2016 IoT botnet malware |
| **Aisuru / Kimwolf** | Recent large IoT / Android TV botnets behind the 2025 record attacks |
| **IoT** | Internet of Things (cameras, routers, TV boxes) |
| **ACL** | Access Control List: firewall rule list |
| **CDN** | Content Delivery Network |
| **Anycast** | The same IP address announced via BGP from many locations; traffic goes to the nearest one |
| **Scrubbing center** | Facility that filters out attack traffic and forwards clean traffic |
| **RTBH** | Remotely Triggered Black Hole: drop all traffic to the attacked IP at the edge or IXP |
| **BCP 38** | Best Current Practice 38 (RFC 2827): ingress filtering against spoofed source addresses |
| **CISA** | US Cybersecurity and Infrastructure Security Agency |
| **eBPF** | extended Berkeley Packet Filter: verified programs running inside the Linux kernel |
| **XDP** | eXpress Data Path: eBPF hook in the network driver for very early packet drops |
| **eBPF map** | Kernel table (e.g. a blocklist) that an eBPF program can look up |
| **L4Drop / dosd / Gatebot** | Cloudflare's XDP packet dropper / DDoS detection service / network-wide attack detector |
| **§ 303b StGB** | German Criminal Code section on computer sabotage |
