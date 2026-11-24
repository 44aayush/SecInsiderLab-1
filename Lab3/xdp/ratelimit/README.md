# Lab 3 Task 4 - XDP per-source-IP rate limiter (Group 8)

`xdp_ratelimit.bpf.c` (78 lines) lets every IPv4 source send 100 packets per
second (`LIMIT_PPS`, fixed 1 s window) and drops the rest in XDP. Per-source counters
are kept in one BPF map, `rl_state` (LRU hash: source IP -> win_start, count,
passed, dropped). No loader program is needed: `ip` attaches the object, `bpftool`
reads the map.

## Build
```
make            # clang -O2 -g -target bpf -mcpu=v3 -> xdp_ratelimit.bpf.o
```

## Test (type these in a terminal, from this folder)

Test bed: one network namespace `atk` holds the attacker (10.0.0.2) and a benign
client (10.0.0.3, a second address on the same interface). It is connected by a
veth pair to the host (10.0.0.1, interface `veth0`), which plays the victim. The
XDP program is attached to `veth0`.

```
script -q task4_run.txt     # optional: records everything below into task4_run.txt

# 1. test bed
sudo ip netns add atk
sudo ip link add veth0 type veth peer name veth1 netns atk
sudo ip addr add 10.0.0.1/24 dev veth0
sudo ip link set veth0 up
sudo ip -n atk addr add 10.0.0.2/24 dev veth1
sudo ip -n atk addr add 10.0.0.3/24 dev veth1
sudo ip -n atk link set veth1 up
ping -c 2 10.0.0.2

# 2. baseline: 5 s SYN flood WITHOUT XDP; IpInReceives = packets that reached the host's IP layer
sudo nstat -n
sudo ip netns exec atk timeout -s INT 5 hping3 -S -p 80 --flood 10.0.0.1
sudo nstat IpInReceives

# 3. attach the rate limiter in generic (skb) mode
sudo ip link set dev veth0 xdpgeneric obj xdp_ratelimit.bpf.o sec xdp
ip link show dev veth0
sudo bpftool prog show name xdp_ratelimit

# 4. same flood WITH XDP, benign ping from 10.0.0.3 at the same time
sudo ip netns exec atk ping -q -c 25 -i 0.2 -I 10.0.0.3 10.0.0.1 > benign.txt &
sudo nstat -n
sudo ip netns exec atk timeout -s INT 5 hping3 -S -p 80 --flood 10.0.0.1
sudo nstat IpInReceives
wait; cat benign.txt

# 5. per-source counters in the BPF map
sudo bpftool map dump name rl_state

# 6. clean up
sudo ip link set dev veth0 xdpgeneric off
sudo ip netns del atk       # also removes veth0
exit                        # stops 'script'
```

## Expected result
- Step 2: IpInReceives is about the number of packets hping3 sent (the whole flood arrives).
- Step 4: IpInReceives is about 500 (100 per second for 5 s), although hping3 sent
  hundreds of thousands of packets; the benign ping has 0 % loss.
- Step 5: `rl_state` has key `[10,0,0,2]` with passed about 500 and a huge `dropped`,
  and key `[10,0,0,3]` with `dropped` 0.

IpInReceives also counts the host's own traffic (browser etc.) and the benign pings, so
it is a little higher than 500; the map counters are exact.

Why IpInReceives and not TcpInSegs: with the ufw firewall on (default: deny incoming),
the SYNs are dropped by netfilter before TCP sees them, so TcpInSegs stays near 0 even
without XDP. IpInReceives is counted when a packet enters the IP layer, before the
firewall, so it shows what passed XDP.
