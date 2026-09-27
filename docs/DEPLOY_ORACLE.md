# Put the Mahsool AI backend on Oracle Cloud (free)

The backend runs 24/7 on a free Oracle Cloud VM. ngrok gives it an HTTPS address
(`https://resident-coil-delusion.ngrok-free.dev`). The website (frontend) is on Vercel and talks to
that address.

You need: an Oracle Cloud account (Always Free), your **Groq API key**, and your **ngrok authtoken**
(ngrok dashboard → "Your Authtoken"). About 45 minutes, most of it waiting.

---

## Step 1. Make an SSH key in Oracle Cloud Shell

1. Log in to https://cloud.oracle.com.
2. Click the **Cloud Shell** icon at the top right (a small `>_` box). A terminal opens at the bottom.
3. Type this and press Enter (press Enter again for every question):
   ```
   ssh-keygen -t ed25519
   ```
4. Show the public key and copy the whole line (it starts with `ssh-ed25519`):
   ```
   cat ~/.ssh/id_ed25519.pub
   ```

## Step 2. Create the VM

1. Menu (☰) → **Compute** → **Instances** → **Create instance**.
2. **Name:** `mahsool`.
3. **Image and shape** → **Edit**:
   - **Image:** click *Change image* → **Canonical Ubuntu** → **24.04** (22.04 also works). Take the
     normal one, **not** "Minimal". Select it.
   - **Shape:** click *Change shape* → **Ampere** → **VM.Standard.A1.Flex**. Set **4 OCPUs** and
     **24 GB** memory. It shows "Always Free-eligible".
4. **Networking:** keep the defaults (new virtual cloud network, public subnet,
   **Assign a public IPv4 address: Yes**).
5. **Add SSH keys:** choose **Paste public keys** and paste the line from Step 1.
6. **Boot volume:** keep the default (about 47 GB is enough; up to 200 GB is free).
7. Click **Show advanced options** → **Management** → **Initialization script** → **Paste cloud-init
   script**. Open [`deploy/oracle/cloud-init.yaml`](../deploy/oracle/cloud-init.yaml) on GitHub,
   click "Raw", copy **everything**, and paste it into the box.
8. Click **Create**. Wait until the state is **Running** (2-3 minutes). Copy the **Public IP address**.

> **"Out of capacity"?** See [Step 6](#step-6-out-of-capacity).

## Step 3. Wait for the install (15-25 minutes)

The VM now installs everything by itself: Python 3.11, ngrok, the code, the libraries, the search
index and the AI models. Nothing needs you. To watch it, in Cloud Shell:

```
ssh ubuntu@PUBLIC_IP
tail -f /var/log/mahsool-install.log
```

(Replace `PUBLIC_IP` with your address. The first time, type `yes`.) The log is finished when you
see `=== [mahsool install] done`. Press **Ctrl+C** to stop watching.

If you see `No such file` for the log, wait 2 minutes and try again (the VM is still starting).

## Step 4. Add your keys (one time)

Still connected to the VM (`ssh ubuntu@PUBLIC_IP`), run:

```
sudo bash /opt/mahsool/deploy/oracle/setup-secrets.sh
```

Paste your **Groq API key**, press Enter. Paste your **ngrok authtoken**, press Enter. The text you
paste is hidden; that is normal. The keys are saved only on the VM (`/opt/mahsool/.env` and
`/opt/mahsool/ngrok.yml`, readable only by the app). They are never in the repo.

## Step 5. Check that it works

Wait 2 minutes (the models load), then:

```
bash /opt/mahsool/deploy/oracle/healthcheck.sh
```

Good result:

```
backend (local):  OK
public (ngrok):   OK  https://resident-coil-delusion.ngrok-free.dev
```

Also open `https://resident-coil-delusion.ngrok-free.dev/health` in your browser (click "Visit
Site" on ngrok's page). You should see `"status":"ok"`. Then open the website on Vercel and ask a
question.

The backend and ngrok start again by themselves after a crash or a reboot.

### Useful commands (on the VM)

| What | Command |
| --- | --- |
| Is it running? | `bash /opt/mahsool/deploy/oracle/healthcheck.sh` |
| Backend log | `journalctl -u mahsool-backend -n 100` |
| ngrok log | `journalctl -u mahsool-ngrok -n 50` |
| Restart | `sudo systemctl restart mahsool-backend mahsool-ngrok` |
| Get the newest code | `sudo bash /opt/mahsool/deploy/oracle/update.sh` |
| Change a key | run `setup-secrets.sh` again |
| Stop the website's backend | `sudo systemctl stop mahsool-ngrok mahsool-backend` |

When the backend is stopped, the website shows "Mahsool AI is resting right now. Please try again
later."

## Step 6. "Out of capacity"

Free Ampere VMs are popular, so Oracle sometimes has none left in your region.

1. Try again in **another Availability Domain** (the "Placement" section, AD-1 / AD-2 / AD-3).
2. Try **smaller**: 2 OCPUs and 12 GB. Mahsool works with that (answers are a bit slower).
3. Try again later: early morning or late night (Pakistan time) often works. Many people need several
   tries over a day or two.
4. Upgrade the account to **Pay As You Go** (Billing → Upgrade). You need a card, but Always Free
   resources stay free, and capacity is much easier to get. Set a **budget alert** (Billing → Budgets,
   e.g. 1 USD) so you hear about any cost at once.

You cannot change your home region, so these are the options.

## Keeping the VM

Oracle may take back an Always Free VM that looks **idle for 7 days** (CPU, network and memory all
below 20%). Mahsool keeps its models in memory (about 5 GB of 24 GB), a health check runs every
5 minutes, and a small daily keep-alive job adds some CPU work. Real visitors help too. The only sure
protection is a **Pay As You Go** account (see Step 6.4): Oracle does not reclaim those VMs.

## Notes

- Only port 22 (SSH) needs to be open. ngrok connects **out** to the internet, so you do not open
  port 80 or 443.
- Questions and feedback are saved in SQLite on the VM (`/opt/mahsool/data/mahsool.db`).
- The free Groq tier gives about 60 new answers a day for everyone; repeated questions come from the
  cache. The website says "come back tomorrow" when the day's answers are used up.
