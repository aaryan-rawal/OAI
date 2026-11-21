import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../auth/AuthProvider";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { TextField } from "../components/ui/Field";
import { usePageTitle } from "../hooks/usePageTitle";

const localNow = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0,16); };
export function DriverRestPage() {
  usePageTitle("Driver rest log");
  const { token } = useAuth();
  const [started, setStarted] = useState(localNow());
  const [ended, setEnded] = useState(localNow());
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState<any>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = async () => {
    if (!token) return;
    const r = await fetch("/api/fleet/me/rest-status", { headers: { Authorization: `Bearer ${token}` } });
    const data = await r.json(); if (!r.ok) throw new Error(data.detail || "Could not load rest status."); setStatus(data);
  };
  useEffect(() => { refresh().catch(e => setMessage(e.message)); }, [token]);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setMessage("");
    try {
      const r = await fetch("/api/fleet/me/rest", { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ started_at: new Date(started).toISOString(), ended_at: new Date(ended).toISOString(), notes }) });
      const data = await r.json(); if (!r.ok) throw new Error(data.detail || "Could not save rest record.");
      setMessage("Rest entry saved as a self-reported record."); await refresh();
    } catch (err) { setMessage(err instanceof Error ? err.message : "Request failed."); }
    finally { setBusy(false); }
  };
  return <div className="stack-lg"><div className="page-head"><div><span className="eyebrow">Driver portal</span><h1>Rest and stop log</h1><p className="muted">Enter your rest period when you stop. This is a self-reported record, not GPS verification.</p></div></div>
    <Card title="Duty status">{status ? <div className="stack"><p><strong>{status.blacklisted ? "Blacklisted" : status.rest_overdue ? "Rest overdue" : "No current blacklist flag"}</strong></p>{status.blacklist_reason && <p className="form-error">{status.blacklist_reason}</p>}<p className="small muted">Active shipment: {status.active_shipment_id || "None"}</p><p className="small muted">Last recorded rest end: {status.last_rest_ended_at || "No rest record"}</p></div> : <p className="muted">Loading status…</p>}</Card>
    <Card title="Record a rest period"><form className="stack" onSubmit={submit}><TextField label="Rest started" type="datetime-local" value={started} onChange={e=>setStarted(e.target.value)} /><TextField label="Rest ended" type="datetime-local" value={ended} onChange={e=>setEnded(e.target.value)} /><TextField label="Notes (optional)" value={notes} onChange={e=>setNotes(e.target.value)} />{message && <p className="banner banner--info" role="status">{message}</p>}<Button type="submit" variant="primary" disabled={busy}>{busy ? "Saving…" : "Submit rest record"}</Button></form></Card>
  </div>;
}
