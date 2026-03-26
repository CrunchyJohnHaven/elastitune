#!/usr/bin/env python3
"""
Security SIEM Benchmark Setup for ElastiTune.

Creates a security-siem index with 300+ documents covering detection rules,
security alerts, threat intelligence, incident reports, and vulnerability
advisories. Also generates an eval-set.json with 15+ search evaluation queries.
"""

import json
import os
import random
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

ES_URL = "http://localhost:9200"
INDEX_NAME = "security-siem"
EVAL_SET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval-set.json")

es = Elasticsearch(ES_URL)

# ---------------------------------------------------------------------------
# 1. Index mapping
# ---------------------------------------------------------------------------
MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
    },
    "mappings": {
        "properties": {
            "title":           {"type": "text"},
            "description":     {"type": "text"},
            "severity":        {"type": "keyword"},
            "category":        {"type": "keyword"},
            "mitre_tactic":    {"type": "keyword"},
            "mitre_technique": {"type": "text"},
            "source":          {"type": "keyword"},
            "tags":            {"type": "keyword"},
        }
    },
}

# ---------------------------------------------------------------------------
# 2. Document corpus
# ---------------------------------------------------------------------------

SEVERITIES = ["critical", "high", "medium", "low", "informational"]

def _docs():
    """Yield all security SIEM documents."""
    doc_id = 0

    # ---- Detection Rules ----
    detection_rules = [
        {
            "title": "PowerShell Encoded Command Execution",
            "description": "Detects execution of PowerShell with Base64 encoded commands, commonly used by attackers to obfuscate malicious payloads and evade signature-based detection systems.",
            "severity": "high",
            "mitre_tactic": "Execution",
            "mitre_technique": "T1059.001 - PowerShell",
            "source": "Sigma",
            "tags": ["powershell", "encoded-command", "obfuscation", "living-off-the-land"],
        },
        {
            "title": "Suspicious DNS Query to Known C2 Domain",
            "description": "Identifies DNS queries resolving to domains associated with known command and control infrastructure. Covers DGA-generated domains and hardcoded C2 addresses used by malware families.",
            "severity": "critical",
            "mitre_tactic": "Command and Control",
            "mitre_technique": "T1071.004 - DNS",
            "source": "Elastic SIEM",
            "tags": ["dns", "c2", "command-and-control", "network", "malware"],
        },
        {
            "title": "Credential Dumping via Mimikatz",
            "description": "Detects processes exhibiting behavior consistent with Mimikatz credential harvesting, including LSASS memory access and Kerberos ticket extraction on Windows endpoints.",
            "severity": "critical",
            "mitre_tactic": "Credential Access",
            "mitre_technique": "T1003.001 - LSASS Memory",
            "source": "Sigma",
            "tags": ["mimikatz", "credential-dumping", "lsass", "windows"],
        },
        {
            "title": "Lateral Movement via PsExec",
            "description": "Detects the use of PsExec or similar remote execution tools to move laterally across Windows hosts within the network, a common post-exploitation technique.",
            "severity": "high",
            "mitre_tactic": "Lateral Movement",
            "mitre_technique": "T1021.002 - SMB/Windows Admin Shares",
            "source": "Elastic SIEM",
            "tags": ["psexec", "lateral-movement", "smb", "windows", "remote-execution"],
        },
        {
            "title": "Scheduled Task Created for Persistence",
            "description": "Monitors for creation of Windows scheduled tasks via schtasks.exe or Task Scheduler API that could be used to maintain persistent access to compromised systems.",
            "severity": "medium",
            "mitre_tactic": "Persistence",
            "mitre_technique": "T1053.005 - Scheduled Task",
            "source": "Sigma",
            "tags": ["persistence", "scheduled-task", "windows", "schtasks"],
        },
        {
            "title": "Suspicious WMI Process Creation",
            "description": "Detects process creation events initiated through Windows Management Instrumentation (WMI), which is frequently abused for remote code execution and lateral movement.",
            "severity": "medium",
            "mitre_tactic": "Execution",
            "mitre_technique": "T1047 - Windows Management Instrumentation",
            "source": "Sigma",
            "tags": ["wmi", "execution", "windows", "remote-execution"],
        },
        {
            "title": "Registry Run Key Modification",
            "description": "Detects modifications to Windows registry Run and RunOnce keys commonly used by malware to achieve persistence across system reboots.",
            "severity": "medium",
            "mitre_tactic": "Persistence",
            "mitre_technique": "T1547.001 - Registry Run Keys",
            "source": "Elastic SIEM",
            "tags": ["registry", "persistence", "windows", "autostart"],
        },
        {
            "title": "DLL Side-Loading Detected",
            "description": "Identifies potential DLL side-loading attacks where a malicious DLL is placed alongside a legitimate application to hijack its execution flow and load attacker-controlled code.",
            "severity": "high",
            "mitre_tactic": "Defense Evasion",
            "mitre_technique": "T1574.002 - DLL Side-Loading",
            "source": "Sigma",
            "tags": ["dll", "side-loading", "defense-evasion", "hijacking"],
        },
        {
            "title": "Kerberoasting Activity Detected",
            "description": "Detects anomalous Kerberos TGS ticket requests targeting service accounts, indicative of Kerberoasting attacks aimed at extracting service account password hashes for offline cracking.",
            "severity": "high",
            "mitre_tactic": "Credential Access",
            "mitre_technique": "T1558.003 - Kerberoasting",
            "source": "Elastic SIEM",
            "tags": ["kerberoasting", "kerberos", "credential-access", "active-directory"],
        },
        {
            "title": "BITS Job Used for File Download",
            "description": "Detects abuse of the Background Intelligent Transfer Service (BITS) to download files from external sources, a technique used to bypass network monitoring and proxy controls.",
            "severity": "medium",
            "mitre_tactic": "Defense Evasion",
            "mitre_technique": "T1197 - BITS Jobs",
            "source": "Sigma",
            "tags": ["bits", "download", "defense-evasion", "living-off-the-land"],
        },
        {
            "title": "Suspicious Outbound Connection on Non-Standard Port",
            "description": "Detects outbound network connections from endpoints to external IPs on unusual ports that may indicate C2 communication or data exfiltration attempts.",
            "severity": "medium",
            "mitre_tactic": "Command and Control",
            "mitre_technique": "T1571 - Non-Standard Port",
            "source": "Elastic SIEM",
            "tags": ["network", "non-standard-port", "c2", "exfiltration"],
        },
        {
            "title": "Macro-Enabled Office Document Execution",
            "description": "Detects execution of VBA macros in Office documents that spawn child processes, a common initial access vector for phishing campaigns delivering malware.",
            "severity": "high",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1566.001 - Spearphishing Attachment",
            "source": "Sigma",
            "tags": ["macro", "office", "phishing", "initial-access", "vba"],
        },
        {
            "title": "Process Injection via CreateRemoteThread",
            "description": "Detects use of CreateRemoteThread API to inject code into remote processes, a technique used to execute malicious code within the address space of legitimate processes.",
            "severity": "high",
            "mitre_tactic": "Defense Evasion",
            "mitre_technique": "T1055.001 - Dynamic-link Library Injection",
            "source": "Elastic SIEM",
            "tags": ["process-injection", "createremotethread", "defense-evasion", "windows"],
        },
        {
            "title": "Suspicious certutil.exe Usage",
            "description": "Detects certutil.exe being used to download files or decode Base64 content, abusing the legitimate Windows certificate utility for malicious file transfer and payload decoding.",
            "severity": "medium",
            "mitre_tactic": "Defense Evasion",
            "mitre_technique": "T1140 - Deobfuscate/Decode Files or Information",
            "source": "Sigma",
            "tags": ["certutil", "download", "decode", "living-off-the-land", "windows"],
        },
        {
            "title": "Data Exfiltration Over DNS Tunneling",
            "description": "Detects unusually large or frequent DNS queries that may indicate DNS tunneling for data exfiltration, including analysis of query length and entropy patterns.",
            "severity": "critical",
            "mitre_tactic": "Exfiltration",
            "mitre_technique": "T1048.001 - Exfiltration Over Symmetric Encrypted Non-C2 Protocol",
            "source": "Elastic SIEM",
            "tags": ["dns-tunneling", "exfiltration", "dns", "data-theft"],
        },
        {
            "title": "Windows Event Log Cleared",
            "description": "Detects clearing of Windows Security, System, or Application event logs, a defense evasion technique used to destroy forensic evidence on compromised systems.",
            "severity": "high",
            "mitre_tactic": "Defense Evasion",
            "mitre_technique": "T1070.001 - Clear Windows Event Logs",
            "source": "Sigma",
            "tags": ["event-log", "cleared", "defense-evasion", "anti-forensics"],
        },
        {
            "title": "RDP Brute Force Attempt",
            "description": "Detects multiple failed RDP authentication attempts from a single source IP followed by a successful login, indicating a potential brute force attack against Remote Desktop Protocol.",
            "severity": "high",
            "mitre_tactic": "Credential Access",
            "mitre_technique": "T1110.001 - Password Guessing",
            "source": "Elastic SIEM",
            "tags": ["rdp", "brute-force", "authentication", "remote-desktop"],
        },
        {
            "title": "Suspicious Parent-Child Process Relationship",
            "description": "Detects anomalous parent-child process relationships such as Word spawning cmd.exe or Excel launching PowerShell, indicative of malicious document exploitation.",
            "severity": "high",
            "mitre_tactic": "Execution",
            "mitre_technique": "T1059 - Command and Scripting Interpreter",
            "source": "Sigma",
            "tags": ["process-tree", "anomaly", "execution", "office-exploit"],
        },
        {
            "title": "Token Impersonation or Theft Detected",
            "description": "Detects attempts to steal or impersonate access tokens to escalate privileges or assume the identity of another user on Windows systems.",
            "severity": "high",
            "mitre_tactic": "Privilege Escalation",
            "mitre_technique": "T1134 - Access Token Manipulation",
            "source": "Elastic SIEM",
            "tags": ["token", "impersonation", "privilege-escalation", "windows"],
        },
        {
            "title": "Linux Reverse Shell Detected",
            "description": "Detects common reverse shell patterns on Linux systems including bash, netcat, and Python-based reverse shells establishing outbound connections to attacker-controlled hosts.",
            "severity": "critical",
            "mitre_tactic": "Execution",
            "mitre_technique": "T1059.004 - Unix Shell",
            "source": "Sigma",
            "tags": ["reverse-shell", "linux", "bash", "netcat", "execution"],
        },
        {
            "title": "Cloud API Key Exfiltration Attempt",
            "description": "Detects attempts to access or exfiltrate cloud service API keys and secrets from environment variables, configuration files, or metadata services.",
            "severity": "critical",
            "mitre_tactic": "Credential Access",
            "mitre_technique": "T1552.005 - Cloud Instance Metadata API",
            "source": "Elastic SIEM",
            "tags": ["cloud", "api-key", "credential-access", "aws", "azure", "gcp"],
        },
        {
            "title": "SSH Tunneling Activity Detected",
            "description": "Detects SSH tunneling and port forwarding activity that may be used to bypass network security controls or establish covert communication channels.",
            "severity": "medium",
            "mitre_tactic": "Command and Control",
            "mitre_technique": "T1572 - Protocol Tunneling",
            "source": "Sigma",
            "tags": ["ssh", "tunneling", "port-forwarding", "network", "evasion"],
        },
        {
            "title": "AMSI Bypass Attempt Detected",
            "description": "Detects attempts to bypass the Antimalware Scan Interface (AMSI) in PowerShell, a technique used to evade script-based malware detection on Windows 10+ systems.",
            "severity": "high",
            "mitre_tactic": "Defense Evasion",
            "mitre_technique": "T1562.001 - Disable or Modify Tools",
            "source": "Elastic SIEM",
            "tags": ["amsi", "bypass", "powershell", "defense-evasion", "windows"],
        },
        {
            "title": "Abnormal Service Installation",
            "description": "Detects installation of new Windows services with suspicious characteristics such as services running from temporary directories or user profile paths.",
            "severity": "medium",
            "mitre_tactic": "Persistence",
            "mitre_technique": "T1543.003 - Windows Service",
            "source": "Sigma",
            "tags": ["service", "persistence", "windows", "installation"],
        },
        {
            "title": "LDAP Reconnaissance Query Detected",
            "description": "Detects LDAP queries commonly associated with Active Directory reconnaissance such as enumeration of domain admins, trusts, and service principal names.",
            "severity": "medium",
            "mitre_tactic": "Discovery",
            "mitre_technique": "T1087.002 - Domain Account",
            "source": "Elastic SIEM",
            "tags": ["ldap", "reconnaissance", "active-directory", "discovery", "enumeration"],
        },
        {
            "title": "Fileless Malware Execution via Mshta",
            "description": "Detects execution of mshta.exe to run inline scripts or fetch remote HTA files, a living-off-the-land technique for fileless malware execution.",
            "severity": "high",
            "mitre_tactic": "Defense Evasion",
            "mitre_technique": "T1218.005 - Mshta",
            "source": "Sigma",
            "tags": ["mshta", "fileless", "living-off-the-land", "defense-evasion"],
        },
        {
            "title": "Cobalt Strike Beacon Activity",
            "description": "Detects network traffic patterns and process behaviors consistent with Cobalt Strike beacon communication, including sleep jitter analysis and named pipe patterns.",
            "severity": "critical",
            "mitre_tactic": "Command and Control",
            "mitre_technique": "T1071.001 - Web Protocols",
            "source": "Elastic SIEM",
            "tags": ["cobalt-strike", "beacon", "c2", "post-exploitation"],
        },
        {
            "title": "UAC Bypass via Fodhelper",
            "description": "Detects User Account Control bypass via fodhelper.exe registry manipulation, allowing elevation of privileges without triggering a UAC prompt.",
            "severity": "high",
            "mitre_tactic": "Privilege Escalation",
            "mitre_technique": "T1548.002 - Bypass User Account Control",
            "source": "Sigma",
            "tags": ["uac", "bypass", "privilege-escalation", "fodhelper", "windows"],
        },
        {
            "title": "Suspicious Cron Job Creation on Linux",
            "description": "Detects creation of new cron jobs that may be used for persistence on Linux systems, including modifications to crontab files and cron directories.",
            "severity": "medium",
            "mitre_tactic": "Persistence",
            "mitre_technique": "T1053.003 - Cron",
            "source": "Elastic SIEM",
            "tags": ["cron", "persistence", "linux", "scheduled-task"],
        },
        {
            "title": "Archive File Created in Staging Directory",
            "description": "Detects creation of archive files (zip, tar, rar, 7z) in common staging directories prior to exfiltration, a technique used to collect and compress data before theft.",
            "severity": "medium",
            "mitre_tactic": "Collection",
            "mitre_technique": "T1560.001 - Archive via Utility",
            "source": "Sigma",
            "tags": ["archive", "staging", "collection", "exfiltration-prep"],
        },
    ]

    for rule in detection_rules:
        doc_id += 1
        yield {
            "_index": INDEX_NAME,
            "_id": str(doc_id),
            "title": rule["title"],
            "description": rule["description"],
            "severity": rule["severity"],
            "category": "detection-rule",
            "mitre_tactic": rule["mitre_tactic"],
            "mitre_technique": rule["mitre_technique"],
            "source": rule["source"],
            "tags": rule["tags"],
        }

    # ---- Security Alerts ----
    security_alerts = [
        {
            "title": "Brute Force Authentication Detected from 10.0.0.50",
            "description": "Multiple failed login attempts (487 in 5 minutes) detected from IP 10.0.0.50 against Active Directory domain controller DC01, targeting multiple user accounts including service accounts.",
            "severity": "high",
            "mitre_tactic": "Credential Access",
            "mitre_technique": "T1110 - Brute Force",
            "source": "Azure Sentinel",
            "tags": ["brute-force", "authentication", "active-directory", "alert"],
        },
        {
            "title": "Ransomware File Encryption Activity",
            "description": "Mass file encryption detected on file server FS01. Over 15,000 files modified with .encrypted extension in 3 minutes. Process csrss_helper.exe identified as responsible. Immediate containment recommended.",
            "severity": "critical",
            "mitre_tactic": "Impact",
            "mitre_technique": "T1486 - Data Encrypted for Impact",
            "source": "CrowdStrike",
            "tags": ["ransomware", "encryption", "file-server", "critical-alert", "impact"],
        },
        {
            "title": "Phishing Email Delivered to Executive Mailbox",
            "description": "Targeted spearphishing email with malicious PDF attachment delivered to CFO mailbox. Email impersonates external legal counsel. Attachment contains embedded JavaScript that downloads second-stage payload.",
            "severity": "high",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1566.001 - Spearphishing Attachment",
            "source": "Proofpoint",
            "tags": ["phishing", "spearphishing", "email", "executive", "initial-access"],
        },
        {
            "title": "Unauthorized Privileged Account Access at 3AM",
            "description": "Domain admin account DA-svc01 authenticated from workstation WS-142 at 03:17 UTC. This account has no authorized after-hours usage. Source IP belongs to the marketing department VLAN.",
            "severity": "high",
            "mitre_tactic": "Privilege Escalation",
            "mitre_technique": "T1078.002 - Domain Accounts",
            "source": "Splunk",
            "tags": ["unauthorized-access", "privilege-escalation", "after-hours", "domain-admin"],
        },
        {
            "title": "Malware Callback to Known Botnet C2 Server",
            "description": "Endpoint WS-089 detected communicating with known TrickBot C2 server at 185.220.101.42:443. HTTPS beacon interval of 60 seconds with jitter. Host may be part of active botnet infection.",
            "severity": "critical",
            "mitre_tactic": "Command and Control",
            "mitre_technique": "T1071.001 - Web Protocols",
            "source": "Palo Alto Cortex",
            "tags": ["botnet", "trickbot", "c2", "malware", "callback"],
        },
        {
            "title": "Data Loss Prevention: Sensitive Data Upload to Cloud Storage",
            "description": "DLP alert triggered for bulk upload of files classified as Confidential-PII to unauthorized Dropbox account. User john.doe uploaded 342 files containing SSN and credit card data.",
            "severity": "critical",
            "mitre_tactic": "Exfiltration",
            "mitre_technique": "T1567.002 - Exfiltration to Cloud Storage",
            "source": "Symantec DLP",
            "tags": ["dlp", "data-loss", "cloud-storage", "pii", "exfiltration"],
        },
        {
            "title": "Suspicious VPN Connection from Sanctioned Country",
            "description": "VPN authentication successful for user accounts from IP addresses geolocated to a sanctioned country. Three separate user accounts authenticated within a 10-minute window.",
            "severity": "high",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1133 - External Remote Services",
            "source": "Cisco ASA",
            "tags": ["vpn", "geolocation", "suspicious-login", "remote-access"],
        },
        {
            "title": "Cryptomining Activity Detected on Server",
            "description": "Server SRV-WEB03 showing sustained 98% CPU utilization. Process analysis reveals xmrig cryptocurrency miner running as a service. Likely compromised through unpatched web application.",
            "severity": "high",
            "mitre_tactic": "Impact",
            "mitre_technique": "T1496 - Resource Hijacking",
            "source": "CrowdStrike",
            "tags": ["cryptomining", "xmrig", "resource-hijacking", "server-compromise"],
        },
        {
            "title": "Anomalous Database Query Volume Detected",
            "description": "Database server DB-PROD01 received 50x normal query volume from application server APP-03. Queries targeting customer PII tables with SELECT * patterns. Possible SQL injection or compromised application.",
            "severity": "high",
            "mitre_tactic": "Collection",
            "mitre_technique": "T1213 - Data from Information Repositories",
            "source": "Imperva",
            "tags": ["database", "anomaly", "sql", "pii", "data-access"],
        },
        {
            "title": "Privilege Escalation via Sudo Exploitation on Linux Host",
            "description": "Alert triggered on Linux host LNX-APP07. User www-data escalated to root via CVE-2021-3156 sudo heap overflow. Suspicious root shell spawned from web server process.",
            "severity": "critical",
            "mitre_tactic": "Privilege Escalation",
            "mitre_technique": "T1068 - Exploitation for Privilege Escalation",
            "source": "Elastic SIEM",
            "tags": ["sudo", "privilege-escalation", "linux", "cve-2021-3156", "exploitation"],
        },
        {
            "title": "Endpoint Detection: Cobalt Strike Payload Identified",
            "description": "EDR detected Cobalt Strike stager shellcode in memory of process svchost.exe (PID 4892) on workstation WS-DEV15. Payload configured to beacon to 192.168.10.99:8443.",
            "severity": "critical",
            "mitre_tactic": "Execution",
            "mitre_technique": "T1055 - Process Injection",
            "source": "SentinelOne",
            "tags": ["cobalt-strike", "edr", "shellcode", "memory", "stager"],
        },
        {
            "title": "Multiple Account Lockouts Across Domain",
            "description": "27 Active Directory accounts locked out within 2 minutes across multiple OUs. Pattern suggests automated password spraying attack against the domain. Source IP traced to compromised print server.",
            "severity": "high",
            "mitre_tactic": "Credential Access",
            "mitre_technique": "T1110.003 - Password Spraying",
            "source": "Azure Sentinel",
            "tags": ["account-lockout", "password-spraying", "active-directory", "automated-attack"],
        },
        {
            "title": "Web Application Firewall: SQL Injection Blocked",
            "description": "WAF blocked 145 SQL injection attempts against /api/v2/users endpoint from IP 203.0.113.42. Attack patterns include UNION SELECT, OR 1=1, and time-based blind injection techniques.",
            "severity": "medium",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "Cloudflare",
            "tags": ["waf", "sql-injection", "web-application", "blocked", "api"],
        },
        {
            "title": "Endpoint Isolation Triggered: WannaCry Variant",
            "description": "Automatic endpoint isolation triggered on WS-FIN04 after detection of WannaCry ransomware variant. SMB propagation attempts to 14 internal hosts were blocked by network segmentation.",
            "severity": "critical",
            "mitre_tactic": "Lateral Movement",
            "mitre_technique": "T1210 - Exploitation of Remote Services",
            "source": "CrowdStrike",
            "tags": ["wannacry", "ransomware", "isolation", "smb", "propagation"],
        },
        {
            "title": "Suspicious Azure AD Sign-In: Impossible Travel",
            "description": "User alice.chen authenticated from New York at 14:00 UTC and from Singapore at 14:15 UTC. Impossible travel detected. Second session accessed SharePoint and downloaded 2GB of engineering documents.",
            "severity": "high",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1078.004 - Cloud Accounts",
            "source": "Azure Sentinel",
            "tags": ["impossible-travel", "azure-ad", "cloud", "account-compromise"],
        },
        {
            "title": "Network Scan Detected from Internal Host",
            "description": "Internal host 10.1.5.22 performed a TCP SYN scan of the entire 10.1.0.0/16 subnet targeting ports 22, 80, 443, 445, 3389. Over 65,000 connection attempts in 10 minutes.",
            "severity": "medium",
            "mitre_tactic": "Discovery",
            "mitre_technique": "T1046 - Network Service Discovery",
            "source": "Darktrace",
            "tags": ["network-scan", "reconnaissance", "internal", "port-scan"],
        },
        {
            "title": "AWS GuardDuty: Unusual API Call from EC2 Instance",
            "description": "EC2 instance i-0abc123 making unusual IAM API calls including ListRoles, GetPolicy, and CreateAccessKey. Instance normally only accesses S3 and DynamoDB. Possible SSRF exploitation.",
            "severity": "high",
            "mitre_tactic": "Discovery",
            "mitre_technique": "T1580 - Cloud Infrastructure Discovery",
            "source": "AWS GuardDuty",
            "tags": ["aws", "guardduty", "iam", "api-abuse", "ssrf", "cloud"],
        },
        {
            "title": "Email Account Compromise: Forwarding Rule Created",
            "description": "Inbox forwarding rule created on executive.vp@company.com directing all emails to external address drop8827@protonmail.com. Rule created from previously unseen IP. Business email compromise suspected.",
            "severity": "high",
            "mitre_tactic": "Collection",
            "mitre_technique": "T1114.003 - Email Forwarding Rule",
            "source": "Microsoft Defender",
            "tags": ["bec", "email-compromise", "forwarding-rule", "executive"],
        },
        {
            "title": "Container Escape Attempt Detected",
            "description": "Kubernetes pod web-frontend-7d8f attempted to mount host filesystem and access Docker socket. Container escape technique detected via CVE-2022-0185 exploitation.",
            "severity": "critical",
            "mitre_tactic": "Privilege Escalation",
            "mitre_technique": "T1611 - Escape to Host",
            "source": "Falco",
            "tags": ["container-escape", "kubernetes", "docker", "privilege-escalation", "cloud-native"],
        },
        {
            "title": "Wireless Rogue Access Point Detected",
            "description": "Unauthorized wireless access point detected on corporate network. SSID 'CorpWiFi-Guest' mimics legitimate corporate SSID. Device MAC address not in approved infrastructure inventory.",
            "severity": "medium",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1200 - Hardware Additions",
            "source": "Cisco Meraki",
            "tags": ["rogue-ap", "wireless", "physical-security", "evil-twin"],
        },
    ]

    for alert in security_alerts:
        doc_id += 1
        yield {
            "_index": INDEX_NAME,
            "_id": str(doc_id),
            "title": alert["title"],
            "description": alert["description"],
            "severity": alert["severity"],
            "category": "security-alert",
            "mitre_tactic": alert["mitre_tactic"],
            "mitre_technique": alert["mitre_technique"],
            "source": alert["source"],
            "tags": alert["tags"],
        }

    # ---- Threat Intelligence ----
    threat_intel = [
        {
            "title": "APT29 Campaign Targeting Government Agencies",
            "description": "Cozy Bear (APT29) attributed campaign targeting government agencies in NATO countries. Uses custom backdoor SunBurst variant delivered through compromised software update mechanism. Focus on foreign affairs and defense ministries.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1195.002 - Compromise Software Supply Chain",
            "source": "Mandiant",
            "tags": ["apt29", "cozy-bear", "government", "supply-chain", "nation-state"],
        },
        {
            "title": "Emotet Botnet Infrastructure Update",
            "description": "Emotet botnet infrastructure has been rebuilt after law enforcement takedown. New C2 servers identified across 47 countries. Updated loader uses 64-bit binaries and enhanced anti-analysis techniques. Distribution via malicious Excel macros.",
            "severity": "high",
            "mitre_tactic": "Command and Control",
            "mitre_technique": "T1071.001 - Web Protocols",
            "source": "Abuse.ch",
            "tags": ["emotet", "botnet", "infrastructure", "loader", "malspam"],
        },
        {
            "title": "Lazarus Group Cryptocurrency Exchange Targeting",
            "description": "North Korean Lazarus Group conducting spearphishing campaign against cryptocurrency exchanges and DeFi platforms. Custom malware AppleJeus used to steal cryptocurrency wallet credentials and private keys.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1566.002 - Spearphishing Link",
            "source": "Kaspersky",
            "tags": ["lazarus", "north-korea", "cryptocurrency", "applejeus", "financial"],
        },
        {
            "title": "FIN7 Point-of-Sale Malware Campaign",
            "description": "FIN7 threat group deploying updated Carbanak backdoor to retail and hospitality sectors. New campaign uses fake job application documents as initial vector. POS malware scrapes payment card data from memory.",
            "severity": "high",
            "mitre_tactic": "Collection",
            "mitre_technique": "T1005 - Data from Local System",
            "source": "FireEye",
            "tags": ["fin7", "carbanak", "pos-malware", "retail", "payment-card"],
        },
        {
            "title": "QakBot Malware Distribution Wave",
            "description": "New QakBot distribution campaign using thread-hijacked emails with OneNote attachments. Payloads download Cobalt Strike for lateral movement. Banking trojan functionality targets financial institutions.",
            "severity": "high",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1566.001 - Spearphishing Attachment",
            "source": "Proofpoint",
            "tags": ["qakbot", "onenote", "thread-hijacking", "banking-trojan"],
        },
        {
            "title": "Volt Typhoon Living-off-the-Land Campaign",
            "description": "Chinese state-sponsored group Volt Typhoon targeting critical infrastructure in the United States. Exclusively uses living-off-the-land techniques with legitimate tools like netsh, PowerShell, and ntdsutil to avoid detection.",
            "severity": "critical",
            "mitre_tactic": "Persistence",
            "mitre_technique": "T1078 - Valid Accounts",
            "source": "CISA",
            "tags": ["volt-typhoon", "china", "critical-infrastructure", "living-off-the-land", "nation-state"],
        },
        {
            "title": "REvil Ransomware-as-a-Service Resurgence",
            "description": "REvil (Sodinokibi) ransomware operation showing renewed activity after infrastructure seizure. New affiliate program offering 80/20 revenue split. Targeting managed service providers for supply chain attacks.",
            "severity": "high",
            "mitre_tactic": "Impact",
            "mitre_technique": "T1486 - Data Encrypted for Impact",
            "source": "Recorded Future",
            "tags": ["revil", "ransomware", "raas", "msp", "supply-chain"],
        },
        {
            "title": "SolarWinds SUNBURST Indicators of Compromise Update",
            "description": "Updated IOC list for SUNBURST backdoor including 18 new C2 domains and 42 new file hashes. Second-stage TEARDROP malware analysis reveals additional persistence mechanisms. Affects SolarWinds Orion versions 2019.4-2020.2.1.",
            "severity": "critical",
            "mitre_tactic": "Command and Control",
            "mitre_technique": "T1071.004 - DNS",
            "source": "FireEye",
            "tags": ["sunburst", "solarwinds", "supply-chain", "ioc", "teardrop"],
        },
        {
            "title": "Conti Ransomware Gang Internal Communications Leaked",
            "description": "Analysis of leaked Conti ransomware gang communications reveals operational procedures, negotiation tactics, and technical infrastructure. Intelligence useful for detection engineering and threat hunting.",
            "severity": "medium",
            "mitre_tactic": "Impact",
            "mitre_technique": "T1486 - Data Encrypted for Impact",
            "source": "Recorded Future",
            "tags": ["conti", "ransomware", "leak", "threat-intelligence", "ttps"],
        },
        {
            "title": "MuddyWater APT Targeting Telecommunications Sector",
            "description": "Iranian state-sponsored group MuddyWater conducting espionage campaign against telecommunications providers in the Middle East. Uses custom PowerShell backdoor PowGoop and Ligolo reverse tunneling tool.",
            "severity": "high",
            "mitre_tactic": "Collection",
            "mitre_technique": "T1119 - Automated Collection",
            "source": "CyberCommand",
            "tags": ["muddywater", "iran", "telecommunications", "espionage", "powgoop"],
        },
        {
            "title": "BazarLoader to Ryuk Ransomware Kill Chain",
            "description": "Threat intelligence report detailing the full kill chain from BazarLoader initial access through Cobalt Strike deployment to Ryuk ransomware execution. Average dwell time of 5 days before encryption. Target selection based on revenue.",
            "severity": "high",
            "mitre_tactic": "Execution",
            "mitre_technique": "T1204.002 - Malicious File",
            "source": "DFIR Report",
            "tags": ["bazarloader", "ryuk", "ransomware", "kill-chain", "cobalt-strike"],
        },
        {
            "title": "Log4Shell Exploitation Campaigns in the Wild",
            "description": "Multiple threat actors exploiting CVE-2021-44228 (Log4Shell) for initial access. Observed payloads include cryptominers, Cobalt Strike beacons, and reverse shells. Targets include VMware Horizon, Apache Solr, and custom Java applications.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "GreyNoise",
            "tags": ["log4shell", "log4j", "cve-2021-44228", "exploitation", "java"],
        },
        {
            "title": "BlackCat ALPHV Ransomware Technical Analysis",
            "description": "Technical analysis of BlackCat (ALPHV) ransomware written in Rust. Features include cross-platform support (Windows/Linux/ESXi), configurable encryption modes, and built-in credential harvesting. Affiliate program uses custom access tokens.",
            "severity": "high",
            "mitre_tactic": "Impact",
            "mitre_technique": "T1486 - Data Encrypted for Impact",
            "source": "Palo Alto Unit 42",
            "tags": ["blackcat", "alphv", "ransomware", "rust", "cross-platform"],
        },
        {
            "title": "Turla Group Watering Hole Campaign",
            "description": "Russian APT Turla compromising government and NGO websites to deliver reconnaissance JavaScript. Infected sites profile visitors and selectively deliver second-stage implants to targets of interest.",
            "severity": "high",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1189 - Drive-by Compromise",
            "source": "ESET",
            "tags": ["turla", "watering-hole", "russia", "government", "reconnaissance"],
        },
        {
            "title": "DarkSide Ransomware Colonial Pipeline Analysis",
            "description": "Post-incident analysis of DarkSide ransomware attack on Colonial Pipeline. Initial access via compromised VPN credential. Ransomware deployed to IT network, OT network not directly affected. $4.4M ransom paid in Bitcoin.",
            "severity": "critical",
            "mitre_tactic": "Impact",
            "mitre_technique": "T1486 - Data Encrypted for Impact",
            "source": "CISA",
            "tags": ["darkside", "ransomware", "colonial-pipeline", "critical-infrastructure", "ot"],
        },
        {
            "title": "Hafnium Exchange Server Exploitation Campaign",
            "description": "Chinese state-sponsored group Hafnium exploiting ProxyLogon vulnerabilities in Microsoft Exchange Servers. Web shells deployed for persistent access. Over 30,000 organizations affected in the United States alone.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "Microsoft MSTIC",
            "tags": ["hafnium", "exchange", "proxylogon", "web-shell", "china"],
        },
        {
            "title": "Sandworm Industroyer2 Targeting Ukrainian Power Grid",
            "description": "Russian GRU-linked Sandworm group deploying Industroyer2 malware targeting Ukrainian electrical substations. ICS-specific malware designed to interact with industrial control protocols including IEC-104.",
            "severity": "critical",
            "mitre_tactic": "Impact",
            "mitre_technique": "T0831 - Manipulation of Control",
            "source": "ESET",
            "tags": ["sandworm", "industroyer", "ics", "ukraine", "power-grid", "ot"],
        },
        {
            "title": "Raccoon Stealer v2 Malware-as-a-Service",
            "description": "Raccoon Stealer v2 (RecordBreaker) available on dark web forums. New version written in C/C++ with improved credential theft capabilities targeting browser passwords, cryptocurrency wallets, and email clients.",
            "severity": "medium",
            "mitre_tactic": "Credential Access",
            "mitre_technique": "T1555.003 - Credentials from Web Browsers",
            "source": "Sekoia",
            "tags": ["raccoon-stealer", "maas", "infostealer", "credentials", "dark-web"],
        },
        {
            "title": "LockBit 3.0 Ransomware Bug Bounty Program",
            "description": "LockBit ransomware operation launched a bug bounty program offering rewards for vulnerabilities in their infrastructure. LockBit 3.0 features anti-analysis protections and new extortion tactics including DDoS threats.",
            "severity": "high",
            "mitre_tactic": "Impact",
            "mitre_technique": "T1486 - Data Encrypted for Impact",
            "source": "Trend Micro",
            "tags": ["lockbit", "ransomware", "bug-bounty", "extortion", "raas"],
        },
        {
            "title": "Kimsuky Social Engineering Campaign Against Researchers",
            "description": "North Korean Kimsuky group targeting cybersecurity researchers and academics through fake conference invitations and research collaboration requests. Custom malware BabyShark delivered via malicious documents.",
            "severity": "high",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1566.001 - Spearphishing Attachment",
            "source": "Google TAG",
            "tags": ["kimsuky", "north-korea", "social-engineering", "researchers", "babyshark"],
        },
    ]

    for ti in threat_intel:
        doc_id += 1
        yield {
            "_index": INDEX_NAME,
            "_id": str(doc_id),
            "title": ti["title"],
            "description": ti["description"],
            "severity": ti["severity"],
            "category": "threat-intelligence",
            "mitre_tactic": ti["mitre_tactic"],
            "mitre_technique": ti["mitre_technique"],
            "source": ti["source"],
            "tags": ti["tags"],
        }

    # ---- Incident Reports ----
    incident_reports = [
        {
            "title": "Supply Chain Compromise via npm Package",
            "description": "Malicious code discovered in popular npm package event-stream (version 3.3.6). Package maintainer account compromised, backdoor added targeting a specific cryptocurrency wallet application. Affected over 8 million weekly downloads.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1195.001 - Compromise Software Dependencies and Development Tools",
            "source": "Internal IR",
            "tags": ["supply-chain", "npm", "javascript", "event-stream", "backdoor"],
        },
        {
            "title": "Insider Threat: Unauthorized Data Access by Employee",
            "description": "Investigation revealed departing employee accessed 47 confidential project repositories and downloaded 12GB of proprietary source code 3 days before resignation. Data exfiltrated via personal USB drive and cloud storage.",
            "severity": "high",
            "mitre_tactic": "Exfiltration",
            "mitre_technique": "T1052.001 - Exfiltration over USB",
            "source": "Internal IR",
            "tags": ["insider-threat", "data-theft", "employee", "source-code", "usb"],
        },
        {
            "title": "Business Email Compromise: Wire Transfer Fraud",
            "description": "CEO email account compromised via credential phishing. Attacker sent convincing wire transfer request to finance department for $2.3M to fraudulent account. $890K transferred before detection. Account takeover lasted 6 days.",
            "severity": "critical",
            "mitre_tactic": "Impact",
            "mitre_technique": "T1565.003 - Runtime Data Manipulation",
            "source": "Internal IR",
            "tags": ["bec", "wire-fraud", "ceo-fraud", "financial-loss", "account-takeover"],
        },
        {
            "title": "Cloud Infrastructure Misconfiguration Data Exposure",
            "description": "Publicly accessible S3 bucket discovered containing 3.2 million customer records including names, emails, and hashed passwords. Bucket misconfigured during migration project. Exposed for approximately 14 days before discovery.",
            "severity": "critical",
            "mitre_tactic": "Collection",
            "mitre_technique": "T1530 - Data from Cloud Storage",
            "source": "Internal IR",
            "tags": ["s3", "misconfiguration", "data-exposure", "cloud", "pii", "aws"],
        },
        {
            "title": "Watering Hole Attack on Industry Conference Website",
            "description": "Cybersecurity conference website compromised to serve drive-by exploit targeting Firefox zero-day. Visitors from specific IP ranges redirected to exploit page. Estimated 400+ potentially compromised attendees.",
            "severity": "high",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1189 - Drive-by Compromise",
            "source": "Internal IR",
            "tags": ["watering-hole", "zero-day", "firefox", "conference", "drive-by"],
        },
        {
            "title": "Ransomware Incident: Manufacturing Plant Shutdown",
            "description": "LockBit ransomware infection caused 72-hour shutdown of manufacturing plant operations. Initial access via exposed RDP server. Active Directory fully compromised within 4 hours. 340 servers and 2,100 workstations encrypted.",
            "severity": "critical",
            "mitre_tactic": "Impact",
            "mitre_technique": "T1486 - Data Encrypted for Impact",
            "source": "Internal IR",
            "tags": ["ransomware", "lockbit", "manufacturing", "operational-impact", "rdp"],
        },
        {
            "title": "Third-Party Vendor Breach Affecting Customer Data",
            "description": "Payment processing vendor breach exposed 1.2 million credit card numbers. Magecart-style skimmer injected into vendor's checkout JavaScript. Cards used for fraudulent transactions within 48 hours of theft.",
            "severity": "critical",
            "mitre_tactic": "Collection",
            "mitre_technique": "T1185 - Browser Session Hijacking",
            "source": "Internal IR",
            "tags": ["vendor-breach", "magecart", "credit-card", "payment", "third-party"],
        },
        {
            "title": "Distributed Denial of Service Attack on Web Infrastructure",
            "description": "Volumetric DDoS attack sustained 2.3 Tbps against public web infrastructure for 18 hours. Attack combined DNS amplification, NTP reflection, and HTTP flood vectors. Partial service degradation for 6 hours despite mitigation.",
            "severity": "high",
            "mitre_tactic": "Impact",
            "mitre_technique": "T1498 - Network Denial of Service",
            "source": "Internal IR",
            "tags": ["ddos", "denial-of-service", "dns-amplification", "web", "availability"],
        },
        {
            "title": "API Key Exposure in Public GitHub Repository",
            "description": "Production API keys for AWS, Stripe, and SendGrid accidentally committed to public GitHub repository by developer. Keys active for 11 hours before automated detection. AWS keys used to spin up 47 EC2 instances for cryptomining.",
            "severity": "high",
            "mitre_tactic": "Credential Access",
            "mitre_technique": "T1552.004 - Private Keys",
            "source": "Internal IR",
            "tags": ["api-key", "github", "exposure", "aws", "credential-leak"],
        },
        {
            "title": "Zero-Day Exploitation of Firewall Appliance",
            "description": "Nation-state actor exploited zero-day vulnerability in Fortinet FortiGate firewall (CVE-2022-42475) to gain access to DMZ network. Custom implant BOLDMOVE deployed for persistent access and internal reconnaissance.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "Internal IR",
            "tags": ["zero-day", "fortinet", "firewall", "nation-state", "dmz"],
        },
        {
            "title": "Compromised CI/CD Pipeline Code Injection",
            "description": "Attacker gained access to Jenkins CI/CD pipeline through stolen service account credentials. Malicious build step injected into deployment pipeline, adding backdoor to production application binaries for 3 weeks before detection.",
            "severity": "critical",
            "mitre_tactic": "Persistence",
            "mitre_technique": "T1195.002 - Compromise Software Supply Chain",
            "source": "Internal IR",
            "tags": ["ci-cd", "jenkins", "pipeline", "supply-chain", "backdoor"],
        },
        {
            "title": "Physical Security Breach: Unauthorized Server Room Access",
            "description": "Unauthorized individual gained physical access to server room by tailgating through badge-controlled door. USB keystroke injection device planted on domain controller. Device discovered during routine hardware audit 5 days later.",
            "severity": "high",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1200 - Hardware Additions",
            "source": "Internal IR",
            "tags": ["physical-security", "tailgating", "rubber-ducky", "server-room", "usb"],
        },
        {
            "title": "Medical Device Network Compromise in Hospital",
            "description": "Network-connected infusion pumps and patient monitors compromised through unpatched vulnerabilities. Attacker pivoted from IoT devices to hospital EHR system. Patient data of 45,000 individuals potentially accessed.",
            "severity": "critical",
            "mitre_tactic": "Lateral Movement",
            "mitre_technique": "T1210 - Exploitation of Remote Services",
            "source": "Internal IR",
            "tags": ["medical-device", "iot", "hospital", "healthcare", "patient-data"],
        },
        {
            "title": "Credential Stuffing Attack on Customer Portal",
            "description": "Automated credential stuffing attack using 12 million username/password combinations from previous breaches. 23,000 customer accounts successfully compromised. Loyalty points and stored payment methods used for fraud.",
            "severity": "high",
            "mitre_tactic": "Credential Access",
            "mitre_technique": "T1110.004 - Credential Stuffing",
            "source": "Internal IR",
            "tags": ["credential-stuffing", "customer-portal", "account-takeover", "fraud"],
        },
        {
            "title": "DNS Hijacking Attack on Financial Services Firm",
            "description": "DNS registrar account for financial services firm compromised. DNS records modified to redirect web traffic through attacker-controlled proxy for 8 hours. TLS certificates obtained via Let's Encrypt. Customer credentials harvested.",
            "severity": "critical",
            "mitre_tactic": "Credential Access",
            "mitre_technique": "T1557 - Adversary-in-the-Middle",
            "source": "Internal IR",
            "tags": ["dns-hijacking", "financial", "mitm", "certificate", "registrar"],
        },
        {
            "title": "Insider Threat: Sabotage of Production Database",
            "description": "Terminated system administrator retained VPN access and used it to drop production database tables 2 weeks after termination. Recovery from backups took 16 hours. Access was not revoked during offboarding process.",
            "severity": "critical",
            "mitre_tactic": "Impact",
            "mitre_technique": "T1485 - Data Destruction",
            "source": "Internal IR",
            "tags": ["insider-threat", "sabotage", "database", "termination", "access-control"],
        },
        {
            "title": "SIM Swapping Attack Against Executive",
            "description": "CFO's mobile phone number ported to attacker-controlled SIM via social engineering of carrier. SMS-based MFA bypassed for email, banking, and corporate VPN. Unauthorized wire transfer of $1.7M initiated.",
            "severity": "critical",
            "mitre_tactic": "Credential Access",
            "mitre_technique": "T1111 - Multi-Factor Authentication Interception",
            "source": "Internal IR",
            "tags": ["sim-swapping", "mfa-bypass", "social-engineering", "executive", "financial"],
        },
        {
            "title": "Kubernetes Cluster Compromise via Exposed Dashboard",
            "description": "Kubernetes dashboard exposed to internet without authentication. Attacker deployed cryptominer pods and established persistent backdoor via CronJob. Cluster contained 120 production microservices. Full rebuild required.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "Internal IR",
            "tags": ["kubernetes", "dashboard", "misconfiguration", "cryptominer", "cloud-native"],
        },
        {
            "title": "Spyware Infection on Executive Mobile Device",
            "description": "Pegasus-like commercial spyware detected on CEO's personal iPhone used for corporate communications. Zero-click exploit via iMessage. Call recordings, messages, and location data exfiltrated for estimated 3 months.",
            "severity": "critical",
            "mitre_tactic": "Collection",
            "mitre_technique": "T1429 - Capture Audio",
            "source": "Internal IR",
            "tags": ["spyware", "pegasus", "mobile", "zero-click", "executive", "surveillance"],
        },
        {
            "title": "Compromised Software Update Server",
            "description": "Internal software update server for proprietary application compromised. Malicious update pushed to 3,400 endpoints containing RAT with keylogging capabilities. Attacker maintained access for 28 days before detection.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1195.002 - Compromise Software Supply Chain",
            "source": "Internal IR",
            "tags": ["software-update", "supply-chain", "rat", "keylogger", "internal"],
        },
    ]

    for report in incident_reports:
        doc_id += 1
        yield {
            "_index": INDEX_NAME,
            "_id": str(doc_id),
            "title": report["title"],
            "description": report["description"],
            "severity": report["severity"],
            "category": "incident-report",
            "mitre_tactic": report["mitre_tactic"],
            "mitre_technique": report["mitre_technique"],
            "source": report["source"],
            "tags": report["tags"],
        }

    # ---- Vulnerability Advisories ----
    vulnerability_advisories = [
        {
            "title": "Critical RCE in Apache Log4j (CVE-2021-44228)",
            "description": "Remote code execution vulnerability in Apache Log4j 2.x (Log4Shell). JNDI lookup feature allows attacker-controlled LDAP/RMI URLs to execute arbitrary code. CVSS 10.0. Affects virtually all Java applications using Log4j for logging.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "NVD",
            "tags": ["log4j", "log4shell", "cve-2021-44228", "rce", "java", "critical"],
        },
        {
            "title": "Exchange Server ProxyShell Exploit Chain",
            "description": "Chain of three vulnerabilities (CVE-2021-34473, CVE-2021-34523, CVE-2021-31207) in Microsoft Exchange Server enabling unauthenticated remote code execution. Pre-auth path confusion, privilege escalation, and post-auth arbitrary file write.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "NVD",
            "tags": ["exchange", "proxyshell", "microsoft", "rce", "exploit-chain"],
        },
        {
            "title": "Spring Framework RCE (Spring4Shell) CVE-2022-22965",
            "description": "Remote code execution in Spring Framework via data binding to ClassLoader. Affects Spring MVC and WebFlux applications running on JDK 9+. Exploitation requires specific deployment configurations including WAR deployment on Tomcat.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "NVD",
            "tags": ["spring4shell", "spring", "java", "rce", "cve-2022-22965"],
        },
        {
            "title": "Follina MSDT Remote Code Execution (CVE-2022-30190)",
            "description": "Zero-day vulnerability in Microsoft Support Diagnostic Tool (MSDT) exploitable via malicious Office documents. No macros required - exploitation through URL protocol handler. Affects all supported Windows versions.",
            "severity": "high",
            "mitre_tactic": "Execution",
            "mitre_technique": "T1203 - Exploitation for Client Execution",
            "source": "NVD",
            "tags": ["follina", "msdt", "zero-day", "office", "cve-2022-30190", "windows"],
        },
        {
            "title": "Apache Struts 2 RCE (CVE-2017-5638)",
            "description": "Critical remote code execution vulnerability in Apache Struts 2 Content-Type header parsing. Exploited in the wild for the Equifax data breach. Allows arbitrary command execution on the server with web application privileges.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "NVD",
            "tags": ["struts", "apache", "rce", "equifax", "cve-2017-5638"],
        },
        {
            "title": "PrintNightmare Windows Print Spooler RCE (CVE-2021-34527)",
            "description": "Remote code execution vulnerability in Windows Print Spooler service. Allows authenticated users to execute arbitrary code with SYSTEM privileges. Proof of concept publicly available. Affects all Windows versions.",
            "severity": "critical",
            "mitre_tactic": "Privilege Escalation",
            "mitre_technique": "T1068 - Exploitation for Privilege Escalation",
            "source": "NVD",
            "tags": ["printnightmare", "print-spooler", "windows", "rce", "cve-2021-34527"],
        },
        {
            "title": "SolarWinds Orion Supply Chain Vulnerability (CVE-2020-10148)",
            "description": "Authentication bypass in SolarWinds Orion API allowing remote code execution. Exploited by UNC2452/APT29 in SUNBURST campaign. Trojanized update delivered to 18,000+ organizations via legitimate software update mechanism.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1195.002 - Compromise Software Supply Chain",
            "source": "NVD",
            "tags": ["solarwinds", "orion", "supply-chain", "sunburst", "cve-2020-10148"],
        },
        {
            "title": "Pulse Secure VPN Arbitrary File Read (CVE-2019-11510)",
            "description": "Pre-auth arbitrary file read vulnerability in Pulse Secure VPN. Allows unauthenticated attackers to read sensitive files including cached credentials. Widely exploited by ransomware groups and APTs for initial access.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "NVD",
            "tags": ["pulse-secure", "vpn", "file-read", "cve-2019-11510", "pre-auth"],
        },
        {
            "title": "Citrix ADC Path Traversal RCE (CVE-2019-19781)",
            "description": "Directory traversal vulnerability in Citrix Application Delivery Controller and Gateway allowing unauthenticated remote code execution. Exploited by multiple threat actors including ransomware gangs and nation-states.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "NVD",
            "tags": ["citrix", "adc", "path-traversal", "rce", "cve-2019-19781"],
        },
        {
            "title": "Confluence Server OGNL Injection (CVE-2022-26134)",
            "description": "Unauthenticated remote code execution via OGNL injection in Atlassian Confluence Server and Data Center. Actively exploited as zero-day. Allows execution of arbitrary code on affected Confluence instances.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "NVD",
            "tags": ["confluence", "atlassian", "ognl", "rce", "cve-2022-26134"],
        },
        {
            "title": "OpenSSL Buffer Overflow (CVE-2022-3602)",
            "description": "High severity buffer overflow in X.509 certificate verification in OpenSSL 3.0.x. Specifically affects punycode processing in certificate name constraint checking. Initially rated critical, downgraded to high after analysis.",
            "severity": "high",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "NVD",
            "tags": ["openssl", "buffer-overflow", "tls", "certificate", "cve-2022-3602"],
        },
        {
            "title": "VMware vCenter Server RCE (CVE-2021-21985)",
            "description": "Remote code execution vulnerability in VMware vCenter Server vSphere Client plugin. Unauthenticated attacker with network access to port 443 can execute arbitrary commands on the host operating system.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "NVD",
            "tags": ["vmware", "vcenter", "rce", "vsphere", "cve-2021-21985"],
        },
        {
            "title": "F5 BIG-IP iControl REST RCE (CVE-2022-1388)",
            "description": "Authentication bypass in F5 BIG-IP iControl REST API allowing unauthenticated remote code execution. Trivial to exploit with publicly available PoC. Affects versions 16.x, 15.x, 14.x, and 13.x of BIG-IP.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "NVD",
            "tags": ["f5", "big-ip", "rce", "authentication-bypass", "cve-2022-1388"],
        },
        {
            "title": "Sudo Heap Overflow Privilege Escalation (CVE-2021-3156)",
            "description": "Heap-based buffer overflow in sudo (Baron Samedit) allowing any local user to escalate to root without authentication. Affects sudo versions 1.8.2 through 1.8.31p2 and 1.9.0 through 1.9.5p1 on Linux and macOS.",
            "severity": "high",
            "mitre_tactic": "Privilege Escalation",
            "mitre_technique": "T1068 - Exploitation for Privilege Escalation",
            "source": "NVD",
            "tags": ["sudo", "privilege-escalation", "linux", "heap-overflow", "cve-2021-3156"],
        },
        {
            "title": "Fortinet FortiOS SSL VPN Path Traversal (CVE-2018-13379)",
            "description": "Path traversal vulnerability in Fortinet FortiOS SSL VPN web portal allowing unauthenticated download of system files including session tokens. Widely exploited for initial access in ransomware campaigns.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "NVD",
            "tags": ["fortinet", "fortios", "vpn", "path-traversal", "cve-2018-13379"],
        },
        {
            "title": "Microsoft NTLM Relay PetitPotam Attack (CVE-2021-36942)",
            "description": "Windows LSA spoofing vulnerability enabling NTLM relay attacks against Active Directory Certificate Services. Allows domain compromise by forcing domain controller authentication to attacker-controlled server.",
            "severity": "high",
            "mitre_tactic": "Credential Access",
            "mitre_technique": "T1557.001 - LLMNR/NBT-NS Poisoning",
            "source": "NVD",
            "tags": ["petitpotam", "ntlm-relay", "active-directory", "adcs", "cve-2021-36942"],
        },
        {
            "title": "Grafana Directory Traversal (CVE-2021-43798)",
            "description": "Path traversal vulnerability in Grafana 8.x allowing unauthenticated users to read arbitrary files from the server. Plugin routes can be abused to traverse out of plugin directory. Database credentials and other secrets at risk.",
            "severity": "high",
            "mitre_tactic": "Collection",
            "mitre_technique": "T1005 - Data from Local System",
            "source": "NVD",
            "tags": ["grafana", "directory-traversal", "file-read", "cve-2021-43798"],
        },
        {
            "title": "MOVEit Transfer SQL Injection (CVE-2023-34362)",
            "description": "Critical SQL injection vulnerability in Progress MOVEit Transfer web application. Exploited by Cl0p ransomware gang for mass data theft from hundreds of organizations. Allows unauthenticated access to database contents.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "NVD",
            "tags": ["moveit", "sql-injection", "cl0p", "mass-exploitation", "cve-2023-34362"],
        },
        {
            "title": "Cisco IOS XE Web UI Privilege Escalation (CVE-2023-20198)",
            "description": "Critical privilege escalation vulnerability in Cisco IOS XE web UI. Allows unauthenticated remote attacker to create a privileged account. Over 40,000 Cisco devices compromised in the wild. CVSS 10.0.",
            "severity": "critical",
            "mitre_tactic": "Privilege Escalation",
            "mitre_technique": "T1068 - Exploitation for Privilege Escalation",
            "source": "NVD",
            "tags": ["cisco", "ios-xe", "privilege-escalation", "cve-2023-20198", "network"],
        },
        {
            "title": "Ivanti Connect Secure Authentication Bypass (CVE-2024-21887)",
            "description": "Command injection vulnerability in web components of Ivanti Connect Secure and Ivanti Policy Secure. When chained with CVE-2023-46805 authentication bypass, allows unauthenticated remote code execution.",
            "severity": "critical",
            "mitre_tactic": "Initial Access",
            "mitre_technique": "T1190 - Exploit Public-Facing Application",
            "source": "NVD",
            "tags": ["ivanti", "connect-secure", "authentication-bypass", "cve-2024-21887", "vpn"],
        },
    ]

    for vuln in vulnerability_advisories:
        doc_id += 1
        yield {
            "_index": INDEX_NAME,
            "_id": str(doc_id),
            "title": vuln["title"],
            "description": vuln["description"],
            "severity": vuln["severity"],
            "category": "vulnerability-advisory",
            "mitre_tactic": vuln["mitre_tactic"],
            "mitre_technique": vuln["mitre_technique"],
            "source": vuln["source"],
            "tags": vuln["tags"],
        }

    # ---- Additional generated documents to reach 300+ ----
    extra_rules = [
        ("Unauthorized Access to Shadow Copy", "Detects access to Volume Shadow Copy service for credential theft or data recovery, commonly used to extract NTDS.dit from domain controllers.", "high", "Credential Access", "T1003.003 - NTDS", "Sigma", ["shadow-copy", "ntds", "credential-theft", "active-directory"]),
        ("Suspicious Network Share Enumeration", "Detects enumeration of network shares using net view or similar tools, indicating reconnaissance activity within the internal network.", "medium", "Discovery", "T1135 - Network Share Discovery", "Elastic SIEM", ["network-shares", "enumeration", "discovery", "reconnaissance"]),
        ("Windows Defender Exclusion Added", "Detects addition of exclusion paths to Windows Defender via PowerShell or registry, a technique used to prevent detection of malicious files.", "medium", "Defense Evasion", "T1562.001 - Disable or Modify Tools", "Sigma", ["windows-defender", "exclusion", "defense-evasion", "av-bypass"]),
        ("Potential Webshell Activity Detected", "Detects web server processes spawning suspicious child processes such as cmd.exe, PowerShell, or bash, indicating potential webshell presence.", "high", "Persistence", "T1505.003 - Web Shell", "Elastic SIEM", ["webshell", "web-server", "persistence", "iis", "apache"]),
        ("Golden Ticket Attack Indicators", "Detects Kerberos TGT with anomalous lifetime or issued from non-DC source, indicating potential Golden Ticket forging for persistent domain access.", "critical", "Persistence", "T1558.001 - Golden Ticket", "Sigma", ["golden-ticket", "kerberos", "persistence", "active-directory"]),
        ("Suspicious PowerShell Download Cradle", "Detects PowerShell commands using common download cradle patterns (IEX, Invoke-WebRequest, Net.WebClient) to download and execute remote payloads.", "high", "Execution", "T1059.001 - PowerShell", "Elastic SIEM", ["powershell", "download-cradle", "iex", "execution"]),
        ("Abnormal SMB Traffic Pattern", "Detects unusual SMB protocol usage patterns including high-volume file access or access from unexpected source IPs, indicating potential ransomware or lateral movement.", "medium", "Lateral Movement", "T1021.002 - SMB/Windows Admin Shares", "Sigma", ["smb", "lateral-movement", "abnormal-traffic", "file-access"]),
        ("Email Attachment with Double Extension", "Detects email attachments with double file extensions (e.g., report.pdf.exe) designed to trick users into executing malicious files.", "medium", "Initial Access", "T1566.001 - Spearphishing Attachment", "Proofpoint", ["email", "double-extension", "phishing", "attachment"]),
        ("Pass-the-Hash Attack Detected", "Detects authentication events where NTLM hashes are used instead of passwords, indicating pass-the-hash lateral movement technique.", "high", "Lateral Movement", "T1550.002 - Pass the Hash", "Elastic SIEM", ["pass-the-hash", "ntlm", "lateral-movement", "authentication"]),
        ("Unauthorized Cloud Resource Provisioning", "Detects creation of compute instances, storage buckets, or network resources by unauthorized users or from unusual locations in cloud environments.", "high", "Impact", "T1578 - Modify Cloud Compute Infrastructure", "AWS CloudTrail", ["cloud", "provisioning", "unauthorized", "aws", "compute"]),
        ("Suspicious Base64 Encoded Registry Value", "Detects creation of registry values containing Base64-encoded data, commonly used to store encoded payloads or configuration for malware persistence.", "medium", "Persistence", "T1547.001 - Registry Run Keys", "Sigma", ["registry", "base64", "encoded", "persistence", "windows"]),
        ("TOR Exit Node Communication Detected", "Detects network traffic to or from known TOR exit nodes, which may indicate anonymized C2 communication or data exfiltration attempts.", "medium", "Command and Control", "T1090.003 - Multi-hop Proxy", "Palo Alto", ["tor", "anonymization", "exit-node", "c2", "proxy"]),
        ("AWS Root Account Login Alert", "Detects login events using the AWS root account, which should never be used for day-to-day operations. May indicate account compromise or policy violation.", "high", "Initial Access", "T1078.004 - Cloud Accounts", "AWS CloudTrail", ["aws", "root-account", "login", "cloud", "policy-violation"]),
        ("Suspicious Named Pipe Creation", "Detects creation of named pipes commonly associated with hacking tools such as Cobalt Strike, Metasploit, and custom C2 frameworks.", "high", "Execution", "T1559 - Inter-Process Communication", "Sigma", ["named-pipe", "cobalt-strike", "metasploit", "ipc"]),
        ("Large Volume of File Deletions Detected", "Detects mass file deletion events that may indicate wiper malware activity, ransomware shadow copy deletion, or intentional data destruction.", "high", "Impact", "T1485 - Data Destruction", "Elastic SIEM", ["file-deletion", "wiper", "data-destruction", "impact"]),
        ("DNS Beacon Activity to DGA Domain", "Detects periodic DNS queries with characteristics of domain generation algorithm (DGA) patterns, indicating potential malware beacon activity.", "high", "Command and Control", "T1568.002 - Domain Generation Algorithms", "Elastic SIEM", ["dga", "dns-beacon", "c2", "malware"]),
        ("Kerberos AS-REP Roasting Detected", "Detects AS-REP roasting attempts targeting accounts with Kerberos pre-authentication disabled, allowing offline password cracking of captured AS-REP responses.", "high", "Credential Access", "T1558.004 - AS-REP Roasting", "Sigma", ["asrep-roasting", "kerberos", "credential-access", "active-directory"]),
        ("Suspicious Office Application Child Process", "Detects Microsoft Office applications spawning scripting interpreters, command shells, or network utilities suggesting macro-based malware execution.", "high", "Execution", "T1204.002 - Malicious File", "Elastic SIEM", ["office", "macro", "child-process", "execution", "malware"]),
        ("Host-Based Firewall Rule Modification", "Detects unauthorized modifications to Windows Firewall or iptables rules that may indicate an attacker opening network paths for lateral movement or exfiltration.", "medium", "Defense Evasion", "T1562.004 - Disable or Modify System Firewall", "Sigma", ["firewall", "rule-modification", "defense-evasion", "network"]),
        ("Anomalous Authentication from Service Account", "Detects interactive logon events from service accounts that should only authenticate non-interactively, indicating potential credential theft.", "high", "Credential Access", "T1078.002 - Domain Accounts", "Elastic SIEM", ["service-account", "interactive-login", "anomaly", "credential-theft"]),
    ]

    extra_alerts = [
        ("AWS S3 Bucket Policy Made Public", "S3 bucket prod-customer-data had its bucket policy changed to allow public read access. Change made by IAM user deploy-bot from IP 54.231.10.99.", "critical", "Collection", "T1530 - Data from Cloud Storage", "AWS CloudTrail", ["s3", "public-access", "aws", "misconfiguration", "data-exposure"]),
        ("Malicious PowerShell Script Blocked by AMSI", "AMSI blocked execution of obfuscated PowerShell script attempting to download and execute Mimikatz from remote server. User workstation WS-MKT05.", "medium", "Defense Evasion", "T1059.001 - PowerShell", "Windows Defender", ["amsi", "powershell", "blocked", "mimikatz"]),
        ("Unauthorized SSH Key Added to Root Account", "New SSH public key added to /root/.ssh/authorized_keys on production server PROD-DB01. Key fingerprint does not match any approved personnel.", "critical", "Persistence", "T1098.004 - SSH Authorized Keys", "OSSEC", ["ssh-key", "unauthorized", "root", "persistence", "linux"]),
        ("Memory-Only Malware Detected by EDR", "Fileless malware detected operating entirely in memory on endpoint WS-HR02. PowerShell reflective DLL injection technique used to load payload without touching disk.", "high", "Defense Evasion", "T1620 - Reflective Code Loading", "CrowdStrike", ["fileless", "memory-only", "reflective-dll", "edr"]),
        ("Suspicious OAuth Application Consent", "User granted permissions to unrecognized OAuth application requesting Mail.Read, Files.ReadWrite.All, and User.ReadBasic.All scopes in Azure AD.", "high", "Credential Access", "T1550.001 - Application Access Token", "Azure Sentinel", ["oauth", "consent-phishing", "azure-ad", "application"]),
        ("ICS SCADA Protocol Anomaly Detected", "Unexpected Modbus TCP write commands detected on OT network targeting PLC controlling pressure valve. Commands originated from engineering workstation outside maintenance window.", "critical", "Impact", "T0831 - Manipulation of Control", "Claroty", ["ics", "scada", "modbus", "ot", "plc", "industrial"]),
        ("Lateral Movement via WinRM Detected", "Windows Remote Management used to execute commands on 12 internal hosts from compromised workstation WS-IT03. Encoded PowerShell payloads observed in WinRM sessions.", "high", "Lateral Movement", "T1021.006 - Windows Remote Management", "Elastic SIEM", ["winrm", "lateral-movement", "powershell", "remote-execution"]),
        ("GitHub Repository Made Public Accidentally", "Private repository containing infrastructure-as-code configurations with embedded secrets was changed to public visibility. Repository contained AWS keys and database passwords.", "critical", "Collection", "T1213.003 - Code Repositories", "GitHub Audit Log", ["github", "public-repo", "secrets", "infrastructure-as-code"]),
        ("Anomalous Outbound Data Transfer Volume", "Workstation WS-ENG09 transferred 45GB of data to external IP over 6 hours. Normal daily outbound for this host is under 500MB. Destination IP linked to file sharing service.", "high", "Exfiltration", "T1048 - Exfiltration Over Alternative Protocol", "Darktrace", ["data-transfer", "exfiltration", "anomaly", "volume"]),
        ("Multi-Factor Authentication Fatigue Attack", "User account bob.smith received 47 MFA push notifications in 30 minutes from different geographic locations. User eventually approved a request. Possible MFA fatigue attack.", "high", "Credential Access", "T1621 - Multi-Factor Authentication Request Generation", "Okta", ["mfa-fatigue", "push-notification", "account-compromise", "okta"]),
    ]

    extra_threat_intel = [
        ("Scattered Spider Social Engineering TTPs", "Analysis of Scattered Spider (UNC3944) social engineering techniques targeting IT help desks. Group uses SIM swapping, MFA fatigue, and convincing phone calls to bypass security controls.", "high", "Initial Access", "T1566.004 - Spearphishing Voice", "Mandiant", ["scattered-spider", "social-engineering", "help-desk", "sim-swapping"]),
        ("Akira Ransomware Technical Profile", "New Akira ransomware group operating since March 2023. Targets VPN vulnerabilities for initial access. Uses Conti-derived codebase. Double extortion with Tor-based leak site.", "high", "Impact", "T1486 - Data Encrypted for Impact", "Sophos", ["akira", "ransomware", "vpn", "double-extortion"]),
        ("Chinese APT41 Supply Chain Operations", "APT41 dual espionage and cybercrime group targeting software supply chains. Recent campaigns compromise build environments to inject backdoors into software updates.", "critical", "Initial Access", "T1195.002 - Compromise Software Supply Chain", "CrowdStrike", ["apt41", "china", "supply-chain", "espionage", "cybercrime"]),
        ("IcedID to Quantum Ransomware Infection Chain", "Documented infection chain from IcedID initial loader through Cobalt Strike deployment to Quantum ransomware. Total time from initial access to encryption: 3 hours 44 minutes.", "high", "Execution", "T1204.002 - Malicious File", "DFIR Report", ["icedid", "quantum", "ransomware", "infection-chain", "cobalt-strike"]),
        ("Play Ransomware Exploitation of FortiOS Vulnerability", "Play ransomware affiliates actively exploiting CVE-2018-13379 and CVE-2020-12812 in FortiOS for initial access. Post-exploitation uses SystemBC proxy and custom .NET tools.", "high", "Initial Access", "T1190 - Exploit Public-Facing Application", "CISA", ["play-ransomware", "fortinet", "exploitation", "systembc"]),
        ("Vice Society Targeting Education Sector", "Vice Society ransomware group disproportionately targeting K-12 schools and universities. Uses multiple ransomware families including Hello Kitty and Zeppelin. Exfiltrates data before encryption.", "high", "Impact", "T1486 - Data Encrypted for Impact", "FBI Flash", ["vice-society", "education", "schools", "ransomware"]),
        ("Gamaredon Group Ukraine Targeting Persistent Campaign", "Russian FSB-linked Gamaredon group maintaining persistent access to Ukrainian government networks through USB-propagating malware and custom backdoors since 2013.", "high", "Persistence", "T1091 - Replication Through Removable Media", "CERT-UA", ["gamaredon", "ukraine", "russia", "usb", "persistent"]),
        ("ALPHV BlackCat Ransomware Healthcare Sector Alert", "ALPHV/BlackCat ransomware group specifically targeting healthcare and hospital networks. Exploitation of ConnectWise ScreenConnect vulnerabilities for initial access.", "critical", "Impact", "T1486 - Data Encrypted for Impact", "HHS HC3", ["alphv", "blackcat", "healthcare", "hospital", "ransomware"]),
        ("TA505 Cl0p Ransomware Zero-Day Exploitation Pattern", "TA505 group behind Cl0p ransomware consistently exploiting zero-day vulnerabilities in file transfer appliances (Accellion, GoAnywhere, MOVEit) for mass data theft.", "critical", "Initial Access", "T1190 - Exploit Public-Facing Application", "Mandiant", ["ta505", "cl0p", "zero-day", "file-transfer", "mass-exploitation"]),
        ("BianLian Ransomware Shift to Pure Extortion", "BianLian ransomware group shifted from encryption-based attacks to pure data theft and extortion model. Targets healthcare, manufacturing, and professional services sectors.", "high", "Impact", "T1657 - Financial Theft", "CISA", ["bianlian", "extortion", "data-theft", "healthcare", "manufacturing"]),
    ]

    extra_vulns = [
        ("GitLab Account Takeover via Password Reset (CVE-2023-7028)", "Critical account takeover vulnerability in GitLab CE/EE. Password reset emails can be delivered to unverified email addresses, allowing attacker to reset any user's password. CVSS 10.0.", "critical", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["gitlab", "account-takeover", "password-reset", "cve-2023-7028"]),
        ("Atlassian Confluence Broken Access Control (CVE-2023-22515)", "Critical broken access control vulnerability in Confluence Data Center and Server. Allows external attackers to create admin accounts and access Confluence instances.", "critical", "Privilege Escalation", "T1068 - Exploitation for Privilege Escalation", "NVD", ["confluence", "atlassian", "access-control", "admin-creation", "cve-2023-22515"]),
        ("Juniper Junos OS Pre-Auth RCE Chain (CVE-2023-36845)", "PHP environment variable manipulation in Juniper SRX and EX series. Chained vulnerabilities allow unauthenticated remote code execution on J-Web interface.", "critical", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["juniper", "junos", "php", "rce", "cve-2023-36845"]),
        ("Apache ActiveMQ RCE (CVE-2023-46604)", "Critical remote code execution in Apache ActiveMQ. Exploitation of OpenWire protocol allows arbitrary command execution. Actively exploited by ransomware groups.", "critical", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["activemq", "apache", "openwire", "rce", "cve-2023-46604"]),
        ("Windows CLFS Driver Privilege Escalation (CVE-2023-28252)", "Zero-day privilege escalation in Windows Common Log File System driver. Exploited by Nokoyawa ransomware group for SYSTEM-level access. Affects all supported Windows versions.", "high", "Privilege Escalation", "T1068 - Exploitation for Privilege Escalation", "NVD", ["clfs", "windows", "privilege-escalation", "nokoyawa", "cve-2023-28252"]),
        ("Barracuda ESG Zero-Day Command Injection (CVE-2023-2868)", "Command injection vulnerability in Barracuda Email Security Gateway. Exploited as zero-day by Chinese APT. Barracuda recommended full device replacement rather than patching.", "critical", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["barracuda", "esg", "command-injection", "china", "cve-2023-2868"]),
        ("Citrix Bleed Information Disclosure (CVE-2023-4966)", "Sensitive information disclosure in Citrix NetScaler ADC and Gateway. Allows session token theft enabling authenticated access bypass. Exploited by LockBit ransomware affiliates.", "critical", "Credential Access", "T1539 - Steal Web Session Cookie", "NVD", ["citrix", "netscaler", "session-hijack", "lockbit", "cve-2023-4966"]),
        ("Zimbra Collaboration XSS to RCE (CVE-2023-37580)", "Cross-site scripting vulnerability in Zimbra Collaboration Suite exploited by four different APT groups. Allows theft of email data and credential harvesting from government targets.", "high", "Initial Access", "T1189 - Drive-by Compromise", "NVD", ["zimbra", "xss", "rce", "email", "cve-2023-37580"]),
        ("ScreenConnect Authentication Bypass (CVE-2024-1709)", "Critical authentication bypass in ConnectWise ScreenConnect allowing unauthorized admin account creation. Trivial exploitation. Widely used by ransomware groups within hours of disclosure.", "critical", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["screenconnect", "connectwise", "auth-bypass", "cve-2024-1709"]),
        ("PAN-OS GlobalProtect Command Injection (CVE-2024-3400)", "Critical command injection in Palo Alto Networks PAN-OS GlobalProtect feature. Unauthenticated attacker can execute arbitrary code with root privileges on the firewall.", "critical", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["palo-alto", "pan-os", "globalprotect", "command-injection", "cve-2024-3400"]),
    ]

    for items, category in [
        (extra_rules, "detection-rule"),
        (extra_alerts, "security-alert"),
        (extra_threat_intel, "threat-intelligence"),
        (extra_vulns, "vulnerability-advisory"),
    ]:
        for title, desc, sev, tactic, tech, src, tags in items:
            doc_id += 1
            yield {
                "_index": INDEX_NAME,
                "_id": str(doc_id),
                "title": title,
                "description": desc,
                "severity": sev,
                "category": category,
                "mitre_tactic": tactic,
                "mitre_technique": tech,
                "source": src,
                "tags": tags,
            }

    # ---- Fill remaining to 310 ----
    additional_misc = [
        ("Threat Hunt: Unusual PowerShell Module Loading", "Proactive threat hunt for PowerShell scripts loading uncommon modules from non-standard paths. Identifies potential attacker tooling being loaded into PowerShell sessions.", "medium", "detection-rule", "Execution", "T1059.001 - PowerShell", "Elastic SIEM", ["threat-hunt", "powershell", "modules", "proactive"]),
        ("Compliance Alert: PCI DSS Log Retention Violation", "Security monitoring identified gaps in log retention for PCI DSS scoped systems. Firewall logs for cardholder data environment not retained for required 12-month period.", "medium", "security-alert", "Collection", "T1005 - Data from Local System", "Splunk", ["compliance", "pci-dss", "log-retention", "audit"]),
        ("Dark Web Monitoring: Employee Credentials Found", "Dark web monitoring service identified 234 employee email/password combinations listed on underground marketplace. Credentials appear sourced from third-party breach.", "high", "threat-intelligence", "Credential Access", "T1589.001 - Credentials", "SpyCloud", ["dark-web", "credentials", "breach", "monitoring"]),
        ("Post-Incident Review: Phishing Campaign Response", "After-action report for Q3 phishing campaign that compromised 12 accounts. Mean time to detect was 4.2 hours. Recommendations include enhanced email filtering and mandatory security training.", "informational", "incident-report", "Initial Access", "T1566 - Phishing", "Internal IR", ["post-incident", "phishing", "review", "lessons-learned"]),
        ("Security Advisory: Chrome V8 Type Confusion (CVE-2023-4863)", "Heap buffer overflow in WebP processing in Google Chrome. Exploited in the wild for zero-click attacks via malicious images. Affects Chrome, Firefox, Edge, and any application using libwebp.", "critical", "vulnerability-advisory", "Execution", "T1203 - Exploitation for Client Execution", "NVD", ["chrome", "webp", "type-confusion", "zero-click", "cve-2023-4863"]),
        ("Threat Hunt: Anomalous Service Account Behavior", "Proactive hunt for service accounts exhibiting interactive logon patterns or accessing resources outside their normal baseline during off-hours periods.", "medium", "detection-rule", "Credential Access", "T1078 - Valid Accounts", "Elastic SIEM", ["threat-hunt", "service-account", "behavior-analysis", "proactive"]),
        ("SOC Playbook: Ransomware Response Procedure", "Standard operating procedure for SOC analysts responding to ransomware alerts. Covers initial triage, containment via network isolation, evidence preservation, and escalation criteria.", "informational", "incident-report", "Impact", "T1486 - Data Encrypted for Impact", "Internal IR", ["soc", "playbook", "ransomware", "response", "procedure"]),
        ("Intel Brief: Emerging Threat Actor Storm-0558", "Microsoft-tracked threat actor Storm-0558 forging Azure AD tokens using acquired Microsoft signing key. Targeted government email accounts. Significant supply chain trust implications.", "critical", "threat-intelligence", "Credential Access", "T1199 - Trusted Relationship", "Microsoft MSTIC", ["storm-0558", "azure-ad", "token-forging", "government", "microsoft"]),
        ("Vulnerability Scan Results: External Attack Surface", "Quarterly external vulnerability scan identified 23 critical, 67 high, and 142 medium findings. Notable: 3 internet-facing servers running End-of-Life software with known exploits.", "high", "vulnerability-advisory", "Discovery", "T1595.002 - Vulnerability Scanning", "Qualys", ["vulnerability-scan", "external", "attack-surface", "eol-software"]),
        ("Detection Engineering: YARA Rule for AsyncRAT", "Custom YARA rule developed for detecting AsyncRAT variants in memory and on disk. Covers packed and unpacked samples with 98.5% detection rate across 500 sample test set.", "medium", "detection-rule", "Command and Control", "T1219 - Remote Access Software", "Internal", ["yara", "asyncrat", "detection-engineering", "custom-rule"]),
    ]

    for title, desc, sev, cat, tactic, tech, src, tags in additional_misc:
        doc_id += 1
        yield {
            "_index": INDEX_NAME,
            "_id": str(doc_id),
            "title": title,
            "description": desc,
            "severity": sev,
            "category": cat,
            "mitre_tactic": tactic,
            "mitre_technique": tech,
            "source": src,
            "tags": tags,
        }

    # ---- Programmatically generated documents to reach 300+ ----
    generated_detection_rules = [
        ("Suspicious WMIC Process Call", "Detects WMIC being used to create processes remotely, a living-off-the-land technique for lateral movement and execution.", "medium", "Execution", "T1047 - Windows Management Instrumentation", "Sigma", ["wmic", "process-call", "execution", "lotl"]),
        ("Browser Password Store Access", "Detects non-browser processes reading browser credential stores (Chrome Login Data, Firefox logins.json).", "medium", "Credential Access", "T1555.003 - Credentials from Web Browsers", "Elastic SIEM", ["browser", "passwords", "credential-theft", "chrome", "firefox"]),
        ("Ntdsutil Active Directory Database Export", "Detects ntdsutil.exe used to create snapshots or export the Active Directory database for offline credential extraction.", "critical", "Credential Access", "T1003.003 - NTDS", "Sigma", ["ntdsutil", "ntds.dit", "active-directory", "credential-dump"]),
        ("Disabling Windows Error Reporting", "Detects attempts to disable Windows Error Reporting service via registry or command, often used to prevent crash dumps that could reveal malware.", "low", "Defense Evasion", "T1112 - Modify Registry", "Elastic SIEM", ["wer", "error-reporting", "registry", "defense-evasion"]),
        ("Suspicious netsh Port Proxy Rule", "Detects netsh commands creating port proxy rules for network traffic forwarding, often used for pivoting.", "medium", "Command and Control", "T1090 - Proxy", "Sigma", ["netsh", "port-proxy", "pivoting", "network"]),
        ("Sysmon Configuration Tampering", "Detects attempts to unload Sysmon driver or modify its configuration to blind security monitoring.", "high", "Defense Evasion", "T1562.001 - Disable or Modify Tools", "Sigma", ["sysmon", "tampering", "evasion", "monitoring"]),
        ("COM Object Hijacking for Persistence", "Detects registry modifications to hijack COM objects for persistence, redirecting legitimate COM calls to malicious DLLs.", "medium", "Persistence", "T1546.015 - Component Object Model Hijacking", "Elastic SIEM", ["com-hijack", "registry", "persistence", "dll"]),
        ("Suspicious MSBuild Execution", "Detects MSBuild.exe being used to compile and execute inline C# code, a signed binary proxy execution technique.", "high", "Defense Evasion", "T1127.001 - MSBuild", "Sigma", ["msbuild", "signed-binary", "proxy-execution", "csharp"]),
        ("DCSync Replication Attack", "Detects domain controller replication requests from non-DC hosts, indicating DCSync attack to extract password hashes.", "critical", "Credential Access", "T1003.006 - DCSync", "Elastic SIEM", ["dcsync", "replication", "active-directory", "password-hashes"]),
        ("Suspicious Print Spooler Service DLL", "Detects loading of unusual DLLs by the print spooler service, potentially indicating PrintNightmare exploitation.", "high", "Privilege Escalation", "T1068 - Exploitation for Privilege Escalation", "Sigma", ["print-spooler", "dll-load", "printnightmare", "privilege-escalation"]),
        ("AppLocker Policy Bypass via Regsvr32", "Detects use of regsvr32.exe to bypass application whitelisting policies by loading remote SCT scripts.", "high", "Defense Evasion", "T1218.010 - Regsvr32", "Elastic SIEM", ["regsvr32", "applocker-bypass", "sct-script", "signed-binary"]),
        ("Suspicious Rundll32 Command Line", "Detects rundll32.exe with suspicious command line arguments including JavaScript, VBScript, or unusual DLL paths.", "medium", "Defense Evasion", "T1218.011 - Rundll32", "Sigma", ["rundll32", "suspicious-args", "script-execution", "lolbin"]),
        ("Windows Credential Manager Access", "Detects tools accessing Windows Credential Manager vaults to extract stored credentials for network resources.", "high", "Credential Access", "T1555.004 - Windows Credential Manager", "Elastic SIEM", ["credential-manager", "vault", "windows", "credential-theft"]),
        ("Azure AD Conditional Access Policy Modification", "Detects modifications to Azure AD Conditional Access policies that could weaken authentication requirements.", "high", "Defense Evasion", "T1556 - Modify Authentication Process", "Azure Sentinel", ["azure-ad", "conditional-access", "policy", "authentication"]),
        ("Suspicious Certreq.exe Usage", "Detects abuse of certreq.exe to download files or exfiltrate data through certificate enrollment requests.", "medium", "Defense Evasion", "T1105 - Ingress Tool Transfer", "Sigma", ["certreq", "download", "exfiltration", "lolbin"]),
        ("Anti-Debugging Techniques Detected", "Detects malware using common anti-debugging techniques such as IsDebuggerPresent, NtQueryInformationProcess, or timing checks.", "medium", "Defense Evasion", "T1622 - Debugger Evasion", "CrowdStrike", ["anti-debugging", "evasion", "malware-analysis", "sandbox"]),
        ("Suspicious Accessibility Features Abuse", "Detects replacement or modification of Windows accessibility features (sethc.exe, utilman.exe) for persistence and backdoor access.", "high", "Persistence", "T1546.008 - Accessibility Features", "Sigma", ["accessibility", "sethc", "utilman", "backdoor", "persistence"]),
        ("Remote Desktop Protocol Tunneling", "Detects RDP connections tunneled through non-standard protocols or tools like plink, chisel, or ngrok.", "high", "Command and Control", "T1572 - Protocol Tunneling", "Elastic SIEM", ["rdp-tunneling", "plink", "chisel", "ngrok", "evasion"]),
        ("Suspicious Startup Folder Modification", "Detects dropping files into Windows Startup folders for persistence, including both user and all-users startup locations.", "medium", "Persistence", "T1547.001 - Registry Run Keys", "Sigma", ["startup-folder", "persistence", "autostart", "windows"]),
        ("DNS-over-HTTPS Detection Evasion", "Detects use of DNS-over-HTTPS to bypass DNS monitoring and filtering controls, potentially hiding C2 communications.", "medium", "Command and Control", "T1071.004 - DNS", "Elastic SIEM", ["doh", "dns-over-https", "evasion", "encrypted-dns"]),
        ("Suspicious Group Policy Object Modification", "Detects modifications to Group Policy Objects that could be used for lateral movement or persistence across domain-joined machines.", "high", "Persistence", "T1484.001 - Group Policy Modification", "Sigma", ["gpo", "group-policy", "active-directory", "persistence"]),
        ("Living Off the Land Binary: Bitsadmin Download", "Detects bitsadmin.exe used to download files from external sources, abusing the legitimate transfer utility.", "medium", "Defense Evasion", "T1197 - BITS Jobs", "Elastic SIEM", ["bitsadmin", "download", "lotl", "transfer"]),
        ("Suspicious Event Tracing for Windows Modification", "Detects tampering with ETW providers to blind security tools that depend on ETW for telemetry collection.", "high", "Defense Evasion", "T1562.006 - Indicator Blocking", "Sigma", ["etw", "tampering", "telemetry", "evasion"]),
        ("Potential Silver Ticket Attack", "Detects forged Kerberos service tickets with anomalous encryption types or issued from non-standard sources.", "high", "Credential Access", "T1558.002 - Silver Ticket", "Elastic SIEM", ["silver-ticket", "kerberos", "forged-ticket", "credential-access"]),
        ("Suspicious InstallUtil.exe Execution", "Detects InstallUtil.exe being used to execute arbitrary .NET assemblies, bypassing application control policies.", "medium", "Defense Evasion", "T1218.004 - InstallUtil", "Sigma", ["installutil", "dotnet", "bypass", "signed-binary"]),
    ]

    generated_alerts = [
        ("Anomalous Login from Legacy Protocol", "Authentication detected using legacy protocol (IMAP/POP3) for account admin@corp.com, bypassing modern authentication and conditional access policies.", "high", "Initial Access", "T1078 - Valid Accounts", "Azure Sentinel", ["legacy-protocol", "imap", "authentication", "bypass"]),
        ("Suspicious Certificate Enrollment Request", "Active Directory Certificate Services received enrollment request for a certificate template allowing domain authentication from non-standard source.", "high", "Credential Access", "T1649 - Steal or Forge Authentication Certificates", "Elastic SIEM", ["adcs", "certificate", "enrollment", "certifried"]),
        ("Cloud Trail Logging Disabled in AWS Region", "CloudTrail logging was disabled in us-east-2 region by IAM user compromised-admin. All API activity in this region is now unmonitored.", "critical", "Defense Evasion", "T1562.008 - Disable Cloud Logs", "AWS CloudTrail", ["cloudtrail", "logging-disabled", "aws", "defense-evasion"]),
        ("Unusual Cross-Tenant Access in Azure", "Azure AD detected authentication from tenant ID not in approved federation list accessing SharePoint and Teams resources.", "high", "Initial Access", "T1078.004 - Cloud Accounts", "Azure Sentinel", ["cross-tenant", "azure", "federation", "unauthorized"]),
        ("Mass Password Reset Activity", "15 password resets performed by helpdesk account in 5-minute window, exceeding normal baseline of 3 per hour. Accounts span multiple departments.", "high", "Persistence", "T1098 - Account Manipulation", "Okta", ["password-reset", "mass-activity", "helpdesk", "anomaly"]),
        ("Endpoint Tampering: Security Agent Uninstalled", "CrowdStrike Falcon sensor forcefully removed from endpoint WS-ACCT03 using uninstallation token. Token source under investigation.", "critical", "Defense Evasion", "T1562.001 - Disable or Modify Tools", "CrowdStrike", ["agent-removal", "edr-tampering", "falcon", "defense-evasion"]),
        ("Suspicious API Gateway Traffic Spike", "API gateway received 50,000 requests per minute to /api/v1/export endpoint from distributed IP addresses, potential automated data scraping.", "high", "Collection", "T1213 - Data from Information Repositories", "AWS WAF", ["api-gateway", "traffic-spike", "scraping", "automation"]),
        ("GCP Service Account Key Created Outside Console", "Service account key for production workload created via API from unrecognized IP address outside of approved CI/CD pipeline.", "high", "Credential Access", "T1552.005 - Cloud Instance Metadata API", "GCP Audit", ["gcp", "service-account", "key-creation", "unauthorized"]),
        ("Bluetooth Keystroke Injection Device Detected", "WIDS detected unauthorized Bluetooth HID device mimicking keyboard within proximity of executive floor. Device broadcasting as 'Logitech KB'.", "medium", "Initial Access", "T1200 - Hardware Additions", "Aruba WIDS", ["bluetooth", "hid", "keystroke-injection", "physical"]),
        ("Suspicious Docker Container with Host Network", "Container launched with --net=host and --privileged flags on production Kubernetes node, potentially enabling network sniffing and host access.", "high", "Privilege Escalation", "T1611 - Escape to Host", "Falco", ["docker", "privileged", "host-network", "container-security"]),
        ("Anomalous Terraform State File Access", "Terraform state file containing infrastructure secrets accessed by unauthorized IAM role from non-CI/CD source.", "high", "Credential Access", "T1552 - Unsecured Credentials", "AWS CloudTrail", ["terraform", "state-file", "secrets", "iac"]),
        ("WAF Bypass Attempt Using Unicode Encoding", "Web application firewall detected repeated attempts to bypass SQL injection rules using Unicode character encoding and double-URL encoding.", "medium", "Initial Access", "T1190 - Exploit Public-Facing Application", "Cloudflare", ["waf-bypass", "unicode", "sql-injection", "encoding"]),
        ("Suspicious Lambda Function Execution", "AWS Lambda function created and executed with full admin permissions from compromised IAM user. Function made API calls to list secrets and export data.", "critical", "Execution", "T1648 - Serverless Execution", "AWS CloudTrail", ["lambda", "serverless", "aws", "admin-privileges"]),
        ("Network Device Configuration Change Alert", "Core router R01-DC1 configuration modified via SSH from unauthorized management station. ACL rules for DMZ segment altered.", "high", "Defense Evasion", "T1599 - Network Boundary Bridging", "Cisco ISE", ["network-device", "config-change", "router", "acl"]),
        ("Suspicious Microsoft Teams Webhook Activity", "Microsoft Teams incoming webhook used to exfiltrate data from internal channels to external endpoint. 500MB transferred in 2 hours.", "high", "Exfiltration", "T1567 - Exfiltration Over Web Service", "Microsoft Defender", ["teams", "webhook", "exfiltration", "data-theft"]),
    ]

    generated_threat_intel_extra = [
        ("NoName057 DDoS Campaign Against NATO Members", "Pro-Russian hacktivist group NoName057(16) conducting sustained DDoS campaigns against government and financial websites in NATO member states using DDoSia tool.", "medium", "Impact", "T1498 - Network Denial of Service", "Sekoia", ["noname057", "ddos", "hacktivist", "russia", "nato"]),
        ("Rhysida Ransomware Targeting Healthcare", "Rhysida ransomware group targeting healthcare and education sectors. Uses phishing for initial access, Cobalt Strike for lateral movement. Double extortion model.", "high", "Impact", "T1486 - Data Encrypted for Impact", "HHS HC3", ["rhysida", "ransomware", "healthcare", "education"]),
        ("SmokeLoader Distribution Campaign Update", "SmokeLoader malware distribution campaign using fake software crack websites and malvertising. Downloads additional payloads including Amadey, RedLine, and SystemBC.", "medium", "Initial Access", "T1189 - Drive-by Compromise", "ANY.RUN", ["smokeloader", "malvertising", "cracks", "loader"]),
        ("Charming Kitten Targeting Journalists", "Iranian APT Charming Kitten targeting journalists and human rights activists with fake interview requests. Uses BASICSTAR backdoor delivered via malicious links.", "high", "Initial Access", "T1566.002 - Spearphishing Link", "Recorded Future", ["charming-kitten", "iran", "journalists", "basicstar"]),
        ("Royal Ransomware Rebrands as BlackSuit", "Royal ransomware operators rebrand as BlackSuit with updated encryptor. Targets critical infrastructure sectors. Estimated $275M in ransom demands since inception.", "high", "Impact", "T1486 - Data Encrypted for Impact", "CISA", ["royal", "blacksuit", "ransomware", "rebrand"]),
        ("Mustang Panda USB Propagation Campaign", "Chinese APT Mustang Panda deploying PlugX malware via USB drives targeting government entities in Southeast Asia. Malware uses DLL side-loading for execution.", "high", "Initial Access", "T1091 - Replication Through Removable Media", "ESET", ["mustang-panda", "plugx", "usb", "china", "southeast-asia"]),
        ("Medusa Ransomware Operations Update", "Medusa ransomware group operating Tor-based leak site with countdown timer. Offers victims options to extend deadline or delete data for cryptocurrency payment.", "high", "Impact", "T1486 - Data Encrypted for Impact", "Palo Alto Unit 42", ["medusa", "ransomware", "tor", "extortion"]),
        ("UNC3886 VMware ESXi Backdoor Campaign", "Chinese espionage group UNC3886 deploying custom backdoors on VMware ESXi hypervisors using zero-day vulnerabilities to maintain persistent access to virtualized environments.", "critical", "Persistence", "T1195.002 - Compromise Software Supply Chain", "Mandiant", ["unc3886", "vmware", "esxi", "hypervisor", "backdoor"]),
        ("FakeBat Loader Malvertising Campaign", "FakeBat loader distributed through Google Ads malvertising impersonating legitimate software downloads. Redirects to lookalike domains hosting trojanized installers.", "medium", "Initial Access", "T1189 - Drive-by Compromise", "Mandiant", ["fakebat", "malvertising", "google-ads", "loader"]),
        ("Volt Typhoon Pre-Positioning in US Critical Infrastructure", "Updated intelligence on Volt Typhoon maintaining persistent access to US critical infrastructure networks for potential future disruptive operations.", "critical", "Persistence", "T1078 - Valid Accounts", "CISA", ["volt-typhoon", "critical-infrastructure", "us", "pre-positioning"]),
    ]

    generated_incidents_extra = [
        ("Unauthorized AI Model Training on Customer Data", "Investigation revealed unauthorized use of customer PII data to train internal ML models without consent. 2.1 million customer records processed. GDPR notification required.", "critical", "incident-report", "Collection", "T1213 - Data from Information Repositories", "Internal IR", ["ai", "ml", "customer-data", "privacy", "gdpr"]),
        ("BGP Hijacking Redirecting Corporate Traffic", "BGP route hijacking incident redirected corporate internet traffic through unauthorized AS for 45 minutes. Affected traffic to payment processing endpoints.", "critical", "incident-report", "Collection", "T1557 - Adversary-in-the-Middle", "Internal IR", ["bgp-hijacking", "routing", "traffic-redirect", "network"]),
        ("Compromised GitHub Actions Workflow", "GitHub Actions workflow in main repository compromised via dependency confusion attack. Malicious package published to internal registry, executed in CI/CD pipeline.", "high", "incident-report", "Execution", "T1195.001 - Compromise Software Dependencies and Development Tools", "Internal IR", ["github-actions", "ci-cd", "dependency-confusion", "supply-chain"]),
        ("Social Engineering Attack on IT Help Desk", "Attacker impersonated senior executive via phone call to IT help desk, convincing analyst to reset MFA and password. Used access to exfiltrate financial projections.", "high", "incident-report", "Initial Access", "T1566.004 - Spearphishing Voice", "Internal IR", ["social-engineering", "help-desk", "impersonation", "mfa-reset"]),
        ("Firmware Implant Discovered on Network Switch", "Routine firmware verification revealed unauthorized modification to network switch firmware in data center. Implant provided covert remote access and traffic mirroring capabilities.", "critical", "incident-report", "Persistence", "T1542.001 - System Firmware", "Internal IR", ["firmware", "implant", "network-switch", "hardware"]),
        ("Mass Account Compromise via SSO Vulnerability", "Vulnerability in SAML SSO implementation allowed authentication bypass. Attacker gained access to 340 user accounts across 12 SaaS applications using forged SAML assertions.", "critical", "incident-report", "Initial Access", "T1078 - Valid Accounts", "Internal IR", ["sso", "saml", "authentication-bypass", "mass-compromise"]),
        ("Cryptographic Key Compromise in PKI Infrastructure", "Root CA private key potentially compromised during infrastructure migration. All certificates issued by subordinate CAs require revocation and reissuance.", "critical", "incident-report", "Credential Access", "T1552.004 - Private Keys", "Internal IR", ["pki", "root-ca", "private-key", "certificate"]),
        ("Data Breach via Compromised Analytics Platform", "Third-party analytics JavaScript library compromised, capturing form data from 23 web applications including login pages. Estimated 180,000 credential pairs exfiltrated.", "critical", "incident-report", "Collection", "T1185 - Browser Session Hijacking", "Internal IR", ["analytics", "javascript", "form-capture", "credentials"]),
        ("Exploitation of Internal Wiki for Credential Harvesting", "Attacker injected credential harvesting page into internal Confluence wiki. Fake SSO login page captured 89 employee credentials over 2 weeks.", "high", "incident-report", "Credential Access", "T1056.003 - Web Portal Capture", "Internal IR", ["confluence", "credential-harvesting", "fake-login", "internal"]),
        ("Ransomware Attack on Backup Infrastructure", "Ransomware operators specifically targeted backup infrastructure (Veeam servers and tape libraries) before encrypting production systems. 95% of backups rendered unusable.", "critical", "incident-report", "Impact", "T1490 - Inhibit System Recovery", "Internal IR", ["ransomware", "backups", "veeam", "recovery", "destruction"]),
    ]

    generated_vulns_extra = [
        ("JetBrains TeamCity Authentication Bypass (CVE-2024-27198)", "Critical authentication bypass in JetBrains TeamCity allowing unauthenticated attacker to take complete control of CI/CD server including source code and build artifacts.", "critical", "vulnerability-advisory", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["teamcity", "jetbrains", "auth-bypass", "ci-cd", "cve-2024-27198"]),
        ("Fortra GoAnywhere MFT RCE (CVE-2023-0669)", "Pre-authentication remote code execution in Fortra GoAnywhere MFT. Exploited by Cl0p ransomware group for mass data theft from enterprise file transfer environments.", "critical", "vulnerability-advisory", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["goanywhere", "fortra", "rce", "cl0p", "cve-2023-0669"]),
        ("Outlook NTLM Relay Zero-Click (CVE-2023-23397)", "Critical zero-click vulnerability in Microsoft Outlook allowing NTLM credential theft via crafted calendar invitation. No user interaction required. Exploited by Russian APT.", "critical", "vulnerability-advisory", "Credential Access", "T1187 - Forced Authentication", "NVD", ["outlook", "ntlm-relay", "zero-click", "calendar", "cve-2023-23397"]),
        ("VMware Aria Operations for Networks RCE (CVE-2023-20887)", "Command injection vulnerability in VMware Aria Operations for Networks allowing unauthenticated RCE via Apache Thrift. Actively exploited in the wild.", "critical", "vulnerability-advisory", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["vmware", "aria", "command-injection", "cve-2023-20887"]),
        ("Windows Win32k Privilege Escalation (CVE-2023-36033)", "Elevation of privilege vulnerability in Windows DWM Core Library. Exploited as zero-day by QakBot operators for SYSTEM-level access on compromised endpoints.", "high", "vulnerability-advisory", "Privilege Escalation", "T1068 - Exploitation for Privilege Escalation", "NVD", ["win32k", "dwm", "privilege-escalation", "qakbot", "cve-2023-36033"]),
        ("Apache Superset Session Validation Bypass (CVE-2023-27524)", "Insecure default SECRET_KEY in Apache Superset allows session token forging and admin access. Affects majority of internet-exposed Superset instances.", "critical", "vulnerability-advisory", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["superset", "apache", "session-forging", "default-key", "cve-2023-27524"]),
        ("SLP Service Amplification DoS (CVE-2023-29552)", "Service Location Protocol (SLP) vulnerability enabling amplification factor of 2,200x for DDoS attacks. Over 54,000 exploitable instances identified globally.", "high", "vulnerability-advisory", "Impact", "T1498 - Network Denial of Service", "NVD", ["slp", "amplification", "ddos", "cve-2023-29552"]),
        ("Papercut NG/MF Server RCE (CVE-2023-27350)", "Critical RCE in PaperCut NG and MF print management servers. Allows unauthenticated attackers to execute code as SYSTEM. Exploited by Cl0p and LockBit ransomware groups.", "critical", "vulnerability-advisory", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["papercut", "print-server", "rce", "cl0p", "cve-2023-27350"]),
        ("HTTP/2 Rapid Reset DoS (CVE-2023-44487)", "Novel DDoS technique exploiting HTTP/2 protocol feature. Record-breaking attacks reaching 398 million requests per second. Affects all HTTP/2 server implementations.", "high", "vulnerability-advisory", "Impact", "T1498 - Network Denial of Service", "NVD", ["http2", "rapid-reset", "ddos", "protocol", "cve-2023-44487"]),
        ("Cisco ASA and FTD Web Services RCE (CVE-2024-20353)", "Combined vulnerabilities in Cisco ASA and Firepower Threat Defense allowing persistent access via webshell. Exploited by state-sponsored actor ArcaneDoor.", "critical", "vulnerability-advisory", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["cisco", "asa", "ftd", "arcanedoor", "cve-2024-20353"]),
    ]

    for title, desc, sev, tactic, tech, src, tags in generated_detection_rules:
        doc_id += 1
        yield {
            "_index": INDEX_NAME,
            "_id": str(doc_id),
            "title": title,
            "description": desc,
            "severity": sev,
            "category": "detection-rule",
            "mitre_tactic": tactic,
            "mitre_technique": tech,
            "source": src,
            "tags": tags,
        }

    for title, desc, sev, tactic, tech, src, tags in generated_alerts:
        doc_id += 1
        yield {
            "_index": INDEX_NAME,
            "_id": str(doc_id),
            "title": title,
            "description": desc,
            "severity": sev,
            "category": "security-alert",
            "mitre_tactic": tactic,
            "mitre_technique": tech,
            "source": src,
            "tags": tags,
        }

    for title, desc, sev, tactic, tech, src, tags in generated_threat_intel_extra:
        doc_id += 1
        yield {
            "_index": INDEX_NAME,
            "_id": str(doc_id),
            "title": title,
            "description": desc,
            "severity": sev,
            "category": "threat-intelligence",
            "mitre_tactic": tactic,
            "mitre_technique": tech,
            "source": src,
            "tags": tags,
        }

    for title, desc, sev, cat, tactic, tech, src, tags in generated_incidents_extra:
        doc_id += 1
        yield {
            "_index": INDEX_NAME,
            "_id": str(doc_id),
            "title": title,
            "description": desc,
            "severity": sev,
            "category": cat,
            "mitre_tactic": tactic,
            "mitre_technique": tech,
            "source": src,
            "tags": tags,
        }

    for title, desc, sev, cat, tactic, tech, src, tags in generated_vulns_extra:
        doc_id += 1
        yield {
            "_index": INDEX_NAME,
            "_id": str(doc_id),
            "title": title,
            "description": desc,
            "severity": sev,
            "category": cat,
            "mitre_tactic": tactic,
            "mitre_technique": tech,
            "source": src,
            "tags": tags,
        }

    # ---- Final batch: more varied security content to exceed 300 ----
    final_batch = [
        ("Suspicious Azure Function App Deployment", "Azure Function App deployed with admin privileges from unrecognized service principal. Function code accesses Key Vault secrets and exfiltrates to external endpoint.", "critical", "security-alert", "Execution", "T1648 - Serverless Execution", "Azure Sentinel", ["azure-functions", "serverless", "key-vault", "exfiltration"]),
        ("Threat Hunt: Living Off the Land in macOS", "Proactive hunt for abuse of macOS built-in tools (osascript, curl, python) for persistence and execution. Targets AppleScript-based payloads and LaunchAgent persistence.", "medium", "detection-rule", "Execution", "T1059.002 - AppleScript", "Elastic SIEM", ["macos", "osascript", "launchagent", "lotl"]),
        ("Supply Chain Risk: Typosquatting PyPI Packages", "Threat intelligence report on typosquatting packages discovered on PyPI targeting popular libraries. Packages contain credential stealers and reverse shells.", "high", "threat-intelligence", "Initial Access", "T1195.001 - Compromise Software Dependencies and Development Tools", "Snyk", ["pypi", "typosquatting", "supply-chain", "python"]),
        ("Post-Breach Assessment: Okta Support System Compromise", "Okta customer support case management system breached. HAR files containing session tokens for customer tenants accessed. All Okta customers advised to rotate credentials.", "critical", "incident-report", "Credential Access", "T1528 - Steal Application Access Token", "Internal IR", ["okta", "support-breach", "session-tokens", "har-files"]),
        ("Cisco IOS Implant Detection via Integrity Verification", "Detection method for identifying unauthorized modifications to Cisco IOS router firmware using memory forensics and hash verification against known-good images.", "high", "detection-rule", "Persistence", "T1542.001 - System Firmware", "Cisco", ["ios", "firmware", "integrity", "router", "forensics"]),
        ("ESXi Ransomware Targeting Virtual Infrastructure", "Multiple ransomware families (ESXiArgs, Royal, BlackBasta) targeting VMware ESXi hypervisors. Exploitation of OpenSLP vulnerability for initial access. Encrypts VMDK files.", "critical", "threat-intelligence", "Impact", "T1486 - Data Encrypted for Impact", "Mandiant", ["esxi", "vmware", "ransomware", "vmdk", "openslp"]),
        ("WordPress Plugin Vulnerability Mass Exploitation", "Critical vulnerability in WordPress plugin (10M+ installations) exploited within 24 hours of disclosure. Attackers injecting SEO spam and backdoor PHP files.", "high", "vulnerability-advisory", "Initial Access", "T1190 - Exploit Public-Facing Application", "Wordfence", ["wordpress", "plugin", "mass-exploitation", "php"]),
        ("Insider Trading via Database Query Analysis", "Forensic analysis revealed finance department employee executing targeted database queries for earnings data 48 hours before public announcement.", "high", "incident-report", "Collection", "T1213 - Data from Information Repositories", "Internal IR", ["insider-trading", "database", "financial", "forensics"]),
        ("QR Code Phishing Campaign Targeting Employees", "Quishing campaign distributing QR codes via email and physical posters directing employees to credential harvesting pages mimicking corporate SSO portal.", "medium", "security-alert", "Initial Access", "T1566 - Phishing", "Proofpoint", ["qr-code", "quishing", "phishing", "sso"]),
        ("AI-Generated Deepfake Voice Used in CEO Fraud", "Threat actors using AI-generated deepfake audio impersonating CEO to authorize fraudulent wire transfers via phone calls to finance department.", "high", "threat-intelligence", "Initial Access", "T1566.004 - Spearphishing Voice", "Recorded Future", ["deepfake", "ai", "voice-fraud", "ceo-fraud", "social-engineering"]),
        ("Exposed GraphQL Introspection Endpoint", "Production GraphQL API discovered with introspection enabled, exposing complete schema including internal mutation endpoints and sensitive data types.", "medium", "vulnerability-advisory", "Discovery", "T1580 - Cloud Infrastructure Discovery", "Internal Scan", ["graphql", "introspection", "api", "schema-exposure"]),
        ("Suspicious Process Hollowing Detected", "EDR detected process hollowing technique where legitimate svchost.exe process memory replaced with malicious code. Maintains legitimate process appearance.", "high", "detection-rule", "Defense Evasion", "T1055.012 - Process Hollowing", "SentinelOne", ["process-hollowing", "svchost", "injection", "evasion"]),
        ("Third-Party Risk: SaaS Vendor Security Assessment Failure", "Annual security assessment of critical SaaS vendor revealed lack of encryption at rest, no SOC 2 Type II, and shared credentials among support staff.", "high", "incident-report", "Collection", "T1199 - Trusted Relationship", "Internal IR", ["third-party-risk", "saas", "vendor", "assessment"]),
        ("Anomalous GPO-Deployed Scheduled Task", "Group Policy Object modified to deploy scheduled task across domain executing encoded PowerShell. Task configured to run as SYSTEM at 2AM across all OUs.", "critical", "security-alert", "Execution", "T1053.005 - Scheduled Task", "Elastic SIEM", ["gpo", "scheduled-task", "powershell", "domain-wide"]),
        ("Microsoft MHTML RCE Zero-Day (CVE-2024-38112)", "Zero-day vulnerability in Windows MSHTML platform exploited via specially crafted .url shortcut files. Allows remote code execution through Internet Explorer rendering engine.", "high", "vulnerability-advisory", "Execution", "T1203 - Exploitation for Client Execution", "NVD", ["mhtml", "mshtml", "zero-day", "url-shortcut", "cve-2024-38112"]),
        ("Typosquatting Domain Alert for Corporate Brand", "Newly registered domains mimicking corporate brand detected: corp-secure-login.com, mycorp-portal.net. Infrastructure analysis links to known phishing operator.", "medium", "threat-intelligence", "Initial Access", "T1583.001 - Domains", "DomainTools", ["typosquatting", "domain", "brand-protection", "phishing-infrastructure"]),
        ("Suspicious DPAPI Master Key Extraction", "Detects attempts to extract DPAPI master keys from domain controller, enabling decryption of all domain user secrets protected by DPAPI.", "critical", "detection-rule", "Credential Access", "T1555 - Credentials from Password Stores", "Sigma", ["dpapi", "master-key", "credential-access", "domain-controller"]),
        ("SOC Metrics: Mean Time to Detect Regression", "SOC performance metrics show MTTD increased from 22 minutes to 4.7 hours for lateral movement detections. Root cause: SIEM rule tuning reduced alert fidelity.", "informational", "incident-report", "Discovery", "T1046 - Network Service Discovery", "Internal IR", ["soc-metrics", "mttd", "performance", "tuning"]),
        ("Network Segmentation Violation Detected", "Production database server DB-PROD-03 received direct connection from guest WiFi VLAN. Firewall rule misconfiguration allowed cross-VLAN traffic.", "high", "security-alert", "Lateral Movement", "T1599 - Network Boundary Bridging", "Cisco ISE", ["segmentation", "vlan", "firewall", "misconfiguration"]),
        ("Threat Actor Profile: FIN11 Evolution", "Updated profile on FIN11 (tracked as TA505/DEV-0950). Group evolved from banking trojans to ransomware operations. Currently primary operator of Cl0p ransomware.", "medium", "threat-intelligence", "Impact", "T1486 - Data Encrypted for Impact", "Mandiant", ["fin11", "ta505", "cl0p", "evolution", "ransomware"]),
    ]

    for title, desc, sev, cat, tactic, tech, src, tags in final_batch:
        doc_id += 1
        yield {
            "_index": INDEX_NAME,
            "_id": str(doc_id),
            "title": title,
            "description": desc,
            "severity": sev,
            "category": cat,
            "mitre_tactic": tactic,
            "mitre_technique": tech,
            "source": src,
            "tags": tags,
        }

    # ---- Padding batch to exceed 300 documents ----
    padding_docs = [
        ("Suspicious PowerShell Remoting Session", "Detects PowerShell remoting connections (WinRM/PSSession) from non-admin workstations, indicating potential lateral movement via PowerShell remote sessions.", "high", "detection-rule", "Lateral Movement", "T1021.006 - Windows Remote Management", "Elastic SIEM", ["powershell-remoting", "winrm", "pssession", "lateral-movement"]),
        ("Anomalous SMB Named Pipe Access", "Detects access to sensitive named pipes (samr, lsarpc, svcctl) from unexpected source hosts, indicating potential remote service manipulation.", "medium", "detection-rule", "Lateral Movement", "T1021.002 - SMB/Windows Admin Shares", "Sigma", ["named-pipe", "smb", "samr", "lsarpc"]),
        ("Cloud Storage Bucket Ransomware Indicator", "Detects mass deletion of S3 object versions followed by upload of encrypted replacements, a cloud-specific ransomware technique.", "critical", "detection-rule", "Impact", "T1486 - Data Encrypted for Impact", "AWS CloudTrail", ["s3-ransomware", "cloud", "encryption", "object-versioning"]),
        ("Suspicious Windows Subsystem for Linux Activity", "Detects use of WSL to execute Linux binaries for defense evasion, as WSL processes may not be monitored by traditional EDR.", "medium", "detection-rule", "Defense Evasion", "T1202 - Indirect Command Execution", "Sigma", ["wsl", "linux", "defense-evasion", "indirect-execution"]),
        ("macOS Gatekeeper Bypass Detected", "Detects attempts to bypass macOS Gatekeeper protections via xattr removal or quarantine flag manipulation on downloaded files.", "high", "detection-rule", "Defense Evasion", "T1553.001 - Gatekeeper Bypass", "Elastic SIEM", ["macos", "gatekeeper", "bypass", "quarantine"]),
        ("Suspicious Azure DevOps Pipeline Modification", "Azure DevOps pipeline definition modified to include steps downloading external scripts. Change made outside normal change window by service connection.", "high", "security-alert", "Execution", "T1195.002 - Compromise Software Supply Chain", "Azure Sentinel", ["azure-devops", "pipeline", "supply-chain", "ci-cd"]),
        ("Credential Harvesting via Internal Phishing Page", "Internal web server hosting credential harvesting page discovered mimicking VPN portal. 43 employee credentials captured before detection.", "high", "security-alert", "Credential Access", "T1056.003 - Web Portal Capture", "Internal IR", ["internal-phishing", "credential-harvesting", "vpn-portal"]),
        ("Suspicious Chrome Extension Installation", "Chrome extension with excessive permissions (all URLs, tabs, storage) installed across 200+ endpoints via GPO. Extension communicates with external C2.", "high", "security-alert", "Persistence", "T1176 - Browser Extensions", "CrowdStrike", ["chrome-extension", "browser", "gpo", "c2"]),
        ("GCP Compute Instance with Crypto Mining", "GCP monitoring detected compute instance e2-highcpu-32 running at 100% CPU. Process analysis confirms XMRig cryptocurrency miner. Instance created with stolen service account.", "high", "security-alert", "Impact", "T1496 - Resource Hijacking", "GCP Security Command Center", ["gcp", "cryptomining", "xmrig", "compute", "cloud"]),
        ("Suspicious LOLBAS: Wscript Remote Script Execution", "Wscript.exe executing VBScript from remote UNC path or URL detected. Living-off-the-land technique to download and execute malicious scripts.", "medium", "detection-rule", "Execution", "T1059.005 - Visual Basic", "Sigma", ["wscript", "vbscript", "lolbas", "remote-execution"]),
        ("Turla ComRAT v4 Communication Pattern", "Network detection for Turla ComRAT v4 backdoor using Gmail as C2 channel via IMAP/SMTP protocols. Unique user-agent and timing patterns identified.", "high", "threat-intelligence", "Command and Control", "T1102 - Web Service", "ESET", ["turla", "comrat", "gmail", "c2", "espionage"]),
        ("Zero-Day Broker Listing: iOS Remote Exploit", "Dark web monitoring detected listing for alleged iOS 17.x remote exploit chain. Asking price $2.5M. Credibility assessment: medium-high based on seller reputation.", "critical", "threat-intelligence", "Initial Access", "T1190 - Exploit Public-Facing Application", "Recorded Future", ["zero-day", "ios", "exploit-broker", "dark-web"]),
        ("SEC Reporting: Material Cybersecurity Incident", "Incident meets SEC materiality threshold requiring 8-K filing. Data breach affecting 500K+ customers with PII exposure. Legal and communications teams engaged.", "critical", "incident-report", "Impact", "T1565 - Data Manipulation", "Internal IR", ["sec-reporting", "8k", "material-incident", "regulatory"]),
        ("Tabletop Exercise: Ransomware Scenario Results", "Annual ransomware tabletop exercise identified gaps in communication plan, backup verification procedures, and decision authority for ransom payment.", "informational", "incident-report", "Impact", "T1486 - Data Encrypted for Impact", "Internal IR", ["tabletop", "exercise", "ransomware", "preparedness"]),
        ("Apple WebKit Zero-Day (CVE-2023-42917)", "Memory corruption vulnerability in Apple WebKit allowing arbitrary code execution when processing malicious web content. Exploited in the wild against iOS devices.", "high", "vulnerability-advisory", "Execution", "T1203 - Exploitation for Client Execution", "NVD", ["apple", "webkit", "ios", "zero-day", "cve-2023-42917"]),
        ("Zyxel Firewall Command Injection (CVE-2023-28771)", "OS command injection in Zyxel firewalls exploitable without authentication via crafted IKEv2 packets. Actively exploited by Mirai botnet variants.", "critical", "vulnerability-advisory", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["zyxel", "firewall", "command-injection", "mirai", "cve-2023-28771"]),
        ("Linux Kernel Netfilter Privilege Escalation (CVE-2023-32233)", "Use-after-free vulnerability in Linux kernel Netfilter nf_tables allowing local privilege escalation to root. Affects kernels 5.x and 6.x.", "high", "vulnerability-advisory", "Privilege Escalation", "T1068 - Exploitation for Privilege Escalation", "NVD", ["linux-kernel", "netfilter", "nf-tables", "privesc", "cve-2023-32233"]),
        ("SAP NetWeaver Deserialization RCE (CVE-2023-25616)", "Critical deserialization vulnerability in SAP NetWeaver AS for Java. Unauthenticated remote code execution via specially crafted serialized objects.", "critical", "vulnerability-advisory", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["sap", "netweaver", "deserialization", "rce", "cve-2023-25616"]),
        ("Redis Unauthorized Access and RCE", "Default Redis installations without authentication accessible from the internet. Attackers writing SSH keys via CONFIG SET for persistent access to underlying host.", "high", "vulnerability-advisory", "Initial Access", "T1190 - Exploit Public-Facing Application", "NVD", ["redis", "unauthorized-access", "ssh-key", "default-config"]),
        ("Suspicious NTFS Alternate Data Stream Usage", "Detects creation or execution of content from NTFS Alternate Data Streams, a technique used to hide malicious payloads within legitimate files.", "medium", "detection-rule", "Defense Evasion", "T1564.004 - NTFS File Attributes", "Sigma", ["ntfs", "ads", "alternate-data-stream", "hiding"]),
        ("Threat Hunt: Proxy Beacon Identification", "Proactive hunt for slow-beacon C2 patterns traversing corporate proxy. Analysis of HTTP(S) traffic metadata for periodic callbacks with consistent intervals.", "medium", "detection-rule", "Command and Control", "T1071.001 - Web Protocols", "Elastic SIEM", ["beacon", "proxy", "c2", "threat-hunt", "periodic"]),
        ("Supply Chain Alert: Compromised Docker Hub Image", "Popular Docker Hub image (5M+ pulls) found containing cryptocurrency miner and reverse shell. Image modified via compromised maintainer account.", "critical", "threat-intelligence", "Initial Access", "T1195.002 - Compromise Software Supply Chain", "Snyk", ["docker-hub", "container", "supply-chain", "cryptominer"]),
        ("Wireless Deauthentication Attack Detected", "Wireless IDS detected mass deauthentication frames targeting corporate SSID. Potential evil twin or client disconnection attack in progress.", "medium", "security-alert", "Initial Access", "T1200 - Hardware Additions", "Aruba WIDS", ["wireless", "deauth", "evil-twin", "wids"]),
        ("Configuration Drift: Production Firewall Rules", "Automated compliance check detected unauthorized firewall rule additions on production perimeter firewall. Rules allow inbound SSH from ANY source.", "high", "security-alert", "Defense Evasion", "T1562.004 - Disable or Modify System Firewall", "Palo Alto Panorama", ["config-drift", "firewall", "compliance", "ssh"]),
        ("AGI Model Extraction Attack on ML Endpoint", "Repeated adversarial queries to production ML model API endpoint consistent with model extraction attack patterns. 2.3M API calls from single account in 48 hours.", "high", "security-alert", "Collection", "T1213 - Data from Information Repositories", "Internal", ["ml-model", "extraction", "adversarial", "api-abuse"]),
        ("Emergency Patch Advisory: Multiple Zero-Days in Browser", "Coordinated disclosure of 3 zero-day vulnerabilities in Chromium-based browsers. Active exploitation confirmed. Emergency patching required for all endpoints.", "critical", "vulnerability-advisory", "Execution", "T1203 - Exploitation for Client Execution", "Google Project Zero", ["chromium", "zero-day", "browser", "emergency-patch"]),
        ("Threat Actor Profile: Midnight Blizzard (APT29) Update", "Updated TTPs for Midnight Blizzard including use of residential proxy networks, OAuth application abuse, and targeting of Microsoft 365 tenants.", "high", "threat-intelligence", "Initial Access", "T1078.004 - Cloud Accounts", "Microsoft MSTIC", ["midnight-blizzard", "apt29", "oauth", "m365", "proxy"]),
        ("Suspicious WinSCP Command-Line File Transfer", "Detects WinSCP.exe command-line usage for automated file transfers to external hosts, potentially used for data staging and exfiltration.", "medium", "detection-rule", "Exfiltration", "T1048 - Exfiltration Over Alternative Protocol", "Sigma", ["winscp", "file-transfer", "exfiltration", "sftp"]),
        ("Database Privilege Escalation via SQL Injection", "Application security scan discovered second-order SQL injection in admin portal allowing database privilege escalation from db_reader to db_owner role.", "high", "vulnerability-advisory", "Privilege Escalation", "T1068 - Exploitation for Privilege Escalation", "Internal Scan", ["sql-injection", "database", "privilege-escalation", "admin-portal"]),
        ("Threat Hunt: Suspicious Parent Process for Certutil", "Hunt for certutil.exe spawned by unexpected parent processes like Office applications, script interpreters, or scheduled tasks.", "medium", "detection-rule", "Defense Evasion", "T1140 - Deobfuscate/Decode Files or Information", "Elastic SIEM", ["certutil", "parent-process", "threat-hunt", "anomaly"]),
        ("North Korean IT Worker Infiltration Alert", "FBI advisory on North Korean IT workers using stolen identities to gain employment at tech companies. Workers use remote access tools and VPNs to obscure location.", "high", "threat-intelligence", "Initial Access", "T1078 - Valid Accounts", "FBI", ["north-korea", "it-workers", "insider", "identity-fraud"]),
        ("Healthcare IoT Device Vulnerability Assessment", "Assessment revealed 847 network-connected medical devices running outdated firmware with known vulnerabilities. 23 devices with critical RCE vulnerabilities in patient care areas.", "critical", "vulnerability-advisory", "Initial Access", "T1190 - Exploit Public-Facing Application", "Internal Scan", ["healthcare", "iot", "medical-devices", "firmware", "assessment"]),
        ("SOC Alert: Impossible Travel for Service Account", "Service account svc-backup authenticated from on-premises data center and AWS us-west-2 region within 2-minute window. Service account should only operate on-premises.", "high", "security-alert", "Initial Access", "T1078 - Valid Accounts", "Azure Sentinel", ["impossible-travel", "service-account", "cloud", "anomaly"]),
        ("Suspicious MSI Installer with Embedded Script", "Detects Windows Installer packages (.msi) containing embedded VBScript or JScript actions that execute during installation, a common malware delivery technique.", "medium", "detection-rule", "Execution", "T1218.007 - Msiexec", "Sigma", ["msi", "installer", "embedded-script", "msiexec"]),
        ("Active Directory Certificate Services Vulnerability (ESC8)", "NTLM relay vulnerability in AD CS web enrollment endpoints. Allows domain escalation by relaying authentication to certificate authority HTTP endpoint.", "high", "vulnerability-advisory", "Privilege Escalation", "T1557.001 - LLMNR/NBT-NS Poisoning", "SpecterOps", ["adcs", "esc8", "ntlm-relay", "certificate", "domain-escalation"]),
        ("Threat Intelligence: Infostealer Logs Market Analysis", "Analysis of 50M+ infostealer logs from Russian Market and Genesis Market. Corporate credentials for Fortune 500 companies identified in 12% of analyzed logs.", "high", "threat-intelligence", "Credential Access", "T1555 - Credentials from Password Stores", "Flare", ["infostealer", "logs", "dark-web", "corporate-credentials"]),
        ("Incident Response: Compromised Email Marketing Platform", "Marketing email platform account compromised and used to send phishing emails to 150K customer email addresses. Brand reputation impact assessment underway.", "high", "incident-report", "Initial Access", "T1566.002 - Spearphishing Link", "Internal IR", ["email-marketing", "brand-abuse", "customer-phishing", "account-compromise"]),
        ("Suspicious LDAP Query for AdminSDHolder", "Detects LDAP queries targeting the AdminSDHolder container, which controls permissions for privileged AD groups. Indicates potential persistence setup via SDProp.", "high", "detection-rule", "Persistence", "T1078.002 - Domain Accounts", "Sigma", ["adminsdholder", "ldap", "sdprop", "active-directory", "persistence"]),
        ("Splunk Universal Forwarder RCE (CVE-2023-46214)", "Remote code execution via XML External Entity injection in Splunk Enterprise. Authenticated users can upload malicious XSLT files to execute arbitrary code.", "high", "vulnerability-advisory", "Execution", "T1203 - Exploitation for Client Execution", "NVD", ["splunk", "xxe", "xslt", "rce", "cve-2023-46214"]),
        ("Anomalous Encryption Activity on File Share", "File share monitoring detected rapid file modification pattern consistent with ransomware: read original, write encrypted copy, delete original. 3,400 files affected in 8 minutes.", "critical", "security-alert", "Impact", "T1486 - Data Encrypted for Impact", "Varonis", ["file-share", "encryption", "ransomware", "monitoring"]),
        ("Cloud Posture: Overly Permissive IAM Policies", "Cloud security posture management found 47 IAM policies with Action: * and Resource: * (full admin). 12 policies attached to service roles accessible from internet-facing applications.", "high", "vulnerability-advisory", "Privilege Escalation", "T1078.004 - Cloud Accounts", "Prisma Cloud", ["iam", "overly-permissive", "cloud-posture", "admin-access"]),
    ]

    for title, desc, sev, cat, tactic, tech, src, tags in padding_docs:
        doc_id += 1
        yield {
            "_index": INDEX_NAME,
            "_id": str(doc_id),
            "title": title,
            "description": desc,
            "severity": sev,
            "category": cat,
            "mitre_tactic": tactic,
            "mitre_technique": tech,
            "source": src,
            "tags": tags,
        }

    print(f"Total documents generated: {doc_id}")


# ---------------------------------------------------------------------------
# 3. Eval set
# ---------------------------------------------------------------------------
EVAL_SET = [
    {
        "id": "siem_eval_001",
        "query": "PowerShell encoded command obfuscation detection",
        "relevantDocIds": ["1", "113", "106"],
        "difficulty": "easy",
        "personaHint": "SOC analyst"
    },
    {
        "id": "siem_eval_002",
        "query": "ransomware file encryption critical alert",
        "relevantDocIds": ["32", "64", "56"],
        "difficulty": "easy",
        "personaHint": "incident responder"
    },
    {
        "id": "siem_eval_003",
        "query": "APT29 nation-state government supply chain attack",
        "relevantDocIds": ["51", "57", "58"],
        "difficulty": "medium",
        "personaHint": "threat intelligence analyst"
    },
    {
        "id": "siem_eval_004",
        "query": "credential dumping LSASS mimikatz windows",
        "relevantDocIds": ["3", "9", "102"],
        "difficulty": "easy",
        "personaHint": "detection engineer"
    },
    {
        "id": "siem_eval_005",
        "query": "Log4j Log4Shell CVE-2021-44228 remote code execution java",
        "relevantDocIds": ["71", "62"],
        "difficulty": "easy",
        "personaHint": "vulnerability analyst"
    },
    {
        "id": "siem_eval_006",
        "query": "lateral movement SMB PsExec remote execution internal network",
        "relevantDocIds": ["4", "107", "109"],
        "difficulty": "medium",
        "personaHint": "threat hunter"
    },
    {
        "id": "siem_eval_007",
        "query": "insider threat employee data theft unauthorized access",
        "relevantDocIds": ["72", "86", "76"],
        "difficulty": "medium",
        "personaHint": "security manager"
    },
    {
        "id": "siem_eval_008",
        "query": "DNS tunneling exfiltration covert channel",
        "relevantDocIds": ["15", "2", "116"],
        "difficulty": "hard",
        "personaHint": "network security analyst"
    },
    {
        "id": "siem_eval_009",
        "query": "Exchange Server ProxyShell vulnerability exploit chain",
        "relevantDocIds": ["72", "66"],
        "difficulty": "easy",
        "personaHint": "vulnerability analyst"
    },
    {
        "id": "siem_eval_010",
        "query": "kubernetes container escape privilege escalation cloud",
        "relevantDocIds": ["49", "88"],
        "difficulty": "medium",
        "personaHint": "cloud security engineer"
    },
    {
        "id": "siem_eval_011",
        "query": "brute force authentication password spraying active directory",
        "relevantDocIds": ["31", "42", "17"],
        "difficulty": "easy",
        "personaHint": "SOC analyst"
    },
    {
        "id": "siem_eval_012",
        "query": "cobalt strike beacon C2 post-exploitation",
        "relevantDocIds": ["27", "41", "114"],
        "difficulty": "medium",
        "personaHint": "threat hunter"
    },
    {
        "id": "siem_eval_013",
        "query": "supply chain software update compromise backdoor",
        "relevantDocIds": ["71", "81", "90", "51"],
        "difficulty": "hard",
        "personaHint": "security architect"
    },
    {
        "id": "siem_eval_014",
        "query": "cloud AWS misconfiguration S3 bucket public exposure",
        "relevantDocIds": ["74", "91"],
        "difficulty": "medium",
        "personaHint": "cloud security engineer"
    },
    {
        "id": "siem_eval_015",
        "query": "phishing spearphishing email macro office initial access",
        "relevantDocIds": ["12", "33", "108", "118"],
        "difficulty": "easy",
        "personaHint": "email security analyst"
    },
    {
        "id": "siem_eval_016",
        "query": "zero-day vulnerability exploitation in the wild",
        "relevantDocIds": ["80", "120", "125", "130"],
        "difficulty": "hard",
        "personaHint": "vulnerability researcher"
    },
    {
        "id": "siem_eval_017",
        "query": "Emotet TrickBot botnet malware distribution campaign",
        "relevantDocIds": ["52", "35"],
        "difficulty": "medium",
        "personaHint": "malware analyst"
    },
    {
        "id": "siem_eval_018",
        "query": "critical infrastructure ICS SCADA industrial control system attack",
        "relevantDocIds": ["67", "96"],
        "difficulty": "hard",
        "personaHint": "OT security specialist"
    },
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # Delete index if exists
    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)
        print(f"Deleted existing index '{INDEX_NAME}'")

    # Create index with mapping
    es.indices.create(index=INDEX_NAME, body=MAPPING)
    print(f"Created index '{INDEX_NAME}' with mapping")

    # Bulk index documents
    success, errors = bulk(es, _docs(), raise_on_error=False, refresh="wait_for")
    print(f"Indexed {success} documents ({errors} errors)")

    # Write eval set
    with open(EVAL_SET_PATH, "w") as f:
        json.dump(EVAL_SET, f, indent=2)
    print(f"Wrote eval-set.json with {len(EVAL_SET)} queries to {EVAL_SET_PATH}")

    # Verify
    count = es.count(index=INDEX_NAME)["count"]
    print(f"Verification: {INDEX_NAME} contains {count} documents")

    # Quick search test
    result = es.search(index=INDEX_NAME, body={
        "query": {"match": {"title": "ransomware"}},
        "size": 3,
    })
    hits = result["hits"]["total"]["value"]
    print(f"Search test: 'ransomware' returned {hits} hits")

    # Category breakdown
    agg = es.search(index=INDEX_NAME, body={
        "size": 0,
        "aggs": {"categories": {"terms": {"field": "category"}}}
    })
    print("\nCategory breakdown:")
    for bucket in agg["aggregations"]["categories"]["buckets"]:
        print(f"  {bucket['key']}: {bucket['doc_count']}")


if __name__ == "__main__":
    main()
