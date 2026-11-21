import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { RegistrationAccountType } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { Button } from "../components/ui/Button";
import { TextField } from "../components/ui/Field";
import { usePageTitle } from "../hooks/usePageTitle";
import { isValidEmail, passwordProblem } from "../lib/validate";

export function RegisterPage() {
  usePageTitle("Create account");
  const { user, completeRegistration } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState(""); const [email, setEmail] = useState("");
  const [phone, setPhone] = useState(""); const [password, setPassword] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [accountType, setAccountType] = useState<RegistrationAccountType>("client");
  const [challenge, setChallenge] = useState<{challenge_id:string; development_otp?:string} | null>(null);
  const [otp, setOtp] = useState(""); const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/" replace />;

  const start = async (event: FormEvent) => {
    event.preventDefault(); setFormError(null);
    if (name.trim().length < 2) return setFormError("Enter your name.");
    if (!isValidEmail(email)) return setFormError("Enter a valid email address.");
    if (phone.replace(/\D/g, "").length < 10) return setFormError("Enter a valid phone number.");
    const pw = passwordProblem(password); if (pw) return setFormError(pw);
    if (accountType === "organization_owner" && organizationName.trim().length < 2) return setFormError("Enter your organization name.");
    setBusy(true);
    try { const result = await api.registerStart({ name, email, phone, password, account_type:accountType, organization_name:organizationName.trim() || undefined }); setChallenge(result); }
    catch (error) { setFormError(error instanceof Error ? error.message : "Could not start registration."); }
    finally { setBusy(false); }
  };
  const verify = async (event: FormEvent) => {
    event.preventDefault(); setFormError(null); setBusy(true);
    try { const session = await api.verifyRegistration({ challenge_id:challenge!.challenge_id, otp }); completeRegistration(session); navigate("/", {replace:true}); }
    catch (error) { setFormError(error instanceof Error ? error.message : "OTP verification failed."); }
    finally { setBusy(false); }
  };

  return <div className="auth-wrap"><div className="card auth-card stack-lg">
    <div className="stack"><span className="eyebrow">OptiFreight AI</span><h1>{challenge ? "Verify your phone" : "Create your account"}</h1>
      <p className="muted">{challenge ? "Enter the one-time code to finish your first-time registration." : "Phone verification is required once, during registration. You can sign in later using your name, phone number or email and password."}</p></div>
    {!challenge ? <form className="stack" onSubmit={start} noValidate>
      <TextField label="Your name" autoComplete="name" value={name} onChange={e=>setName(e.target.value)} />
      <TextField label="Email" type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} />
      <TextField label="Phone number" type="tel" autoComplete="tel" hint="Include country code, for example +91." value={phone} onChange={e=>setPhone(e.target.value)} />
      <TextField label="Password" type="password" autoComplete="new-password" hint="At least 8 characters." value={password} onChange={e=>setPassword(e.target.value)} />
      <label className="field"><span className="field__label">Account type</span><select className="field__control" value={accountType} onChange={e=>setAccountType(e.target.value as RegistrationAccountType)}><option value="client">Client</option><option value="organization_owner">Owner</option><option value="driver">Container driver</option></select></label>
      {accountType === "organization_owner" && <TextField label="Organization name" value={organizationName} onChange={e=>setOrganizationName(e.target.value)} />}
      {formError && <p className="form-error" role="alert">{formError}</p>}
      <Button type="submit" variant="primary" block disabled={busy}>{busy ? "Starting…" : "Send verification code"}</Button>
    </form> : <form className="stack" onSubmit={verify}>
      {challenge.development_otp && <p className="banner banner--demo">Local development OTP: <strong>{challenge.development_otp}</strong>. Production SMS delivery requires a configured SMS provider.</p>}
      <TextField label="6-digit OTP" inputMode="numeric" autoComplete="one-time-code" value={otp} onChange={e=>setOtp(e.target.value.replace(/\D/g,"").slice(0,6))} />
      {formError && <p className="form-error" role="alert">{formError}</p>}
      <Button type="submit" variant="primary" block disabled={busy || otp.length !== 6}>{busy ? "Verifying…" : "Verify and create account"}</Button>
      <button type="button" className="button button--secondary" onClick={()=>{setChallenge(null);setOtp("");}}>Back</button>
    </form>}
    <p className="small">Already have an account? <Link to="/login">Sign in</Link></p>
  </div></div>;
}
