# DMARC Record for nobulex.com

Add this TXT record to your Namecheap DNS settings:

**Host/Name:** _dmarc
**Type:** TXT
**Value:** v=DMARC1; p=none; rua=mailto:postmaster@nobulex.com; ruf=mailto:postmaster@nobulex.com; fo=1

## Full DMARC Configuration Details:

### Record Type: TXT
### Host: _dmarc
### Value: v=DMARC1; p=none; rua=mailto:postmaster@nobulex.com; ruf=mailto:postmaster@nobulex.com; fo=1

### Field Explanations:
- **v=DMARC1** — DMARC version (always 1)
- **p=none** — Policy set to "none" (monitoring only, no rejection)
  - Can be upgraded to "quarantine" or "reject" after monitoring
- **rua=mailto:** — Where to send aggregate reports (weekly)
- **ruf=mailto:** — Where to send forensic reports (on failure)
- **fo=1** — Generate reports if any mechanism fails

## Steps to Add in Namecheap:

1. Log in to Namecheap.com
2. Go to "Dashboard" → "Domain List"
3. Click "Manage" next to nobulex.com
4. Go to "Advanced DNS" tab
5. Click "Add Record"
6. Select Type: **TXT**
7. Host: **_dmarc**
8. Value: **v=DMARC1; p=none; rua=mailto:postmaster@nobulex.com; ruf=mailto:postmaster@nobulex.com; fo=1**
9. TTL: 3600 (default)
10. Click the checkmark to save

## Verification:

After 24-48 hours, verify with:
```bash
nslookup -type=TXT _dmarc.nobulex.com
```

Or check with online tools:
- mxtoolbox.com
- dmarcian.com
- agari.com