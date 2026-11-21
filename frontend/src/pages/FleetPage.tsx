import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { CircleMarker, Tooltip } from "react-leaflet";
import type { FleetContainer } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { MapView } from "../components/map/MapView";
import { Button, ButtonLink } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { SelectField, TextAreaField, TextField } from "../components/ui/Field";
import { usePageTitle } from "../hooks/usePageTitle";
import {
  useAddFleetContainer,
  useAddFleetDriver,
  useDeleteFleetContainer,
  useDeleteFleetDriver,
  useFleetContainers,
  useFleetDrivers,
  useShipments,
  useUpdateFleetContainer,
} from "../hooks/useApiData";
import { isActive, STATUS_LABEL } from "../lib/shipment";
import { useWorkspace } from "../state/WorkspaceContext";

function errorText(error: unknown): string | null {
  return error instanceof Error ? error.message : error ? "The request failed." : null;
}


function DriverVerification({ driver, token }: { driver: { id: string; name: string; date_of_birth?: string | null; verification_status?: string }; token: string | null }) {
  const [dob, setDob] = useState(driver.date_of_birth ?? "");
  const [license, setLicense] = useState(""); const [pan, setPan] = useState(""); const [aadhaar, setAadhaar] = useState("");
  const [files, setFiles] = useState<Record<string, File | null>>({}); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault(); if (!token) return; setBusy(true); setMessage("");
    try {
      for (const type of ["driving_license", "pan", "aadhaar"]) {
        const file = files[type]; if (!file) continue;
        const form = new FormData(); form.append("file", file);
        const uploaded = await fetch(`/api/documents/drivers/${driver.id}/${type}`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form });
        const body = await uploaded.json(); if (!uploaded.ok) throw new Error(body.detail || `Could not upload ${type} document.`);
      }
      if (license && pan && aadhaar && dob) {
        const response = await fetch(`/api/fleet/drivers/${driver.id}/verify`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ full_name: driver.name, date_of_birth: dob, driving_license_number: license, pan_number: pan, aadhaar_number: aadhaar }) });
        const body = await response.json(); if (!response.ok) throw new Error(body.detail || "Identity verification request failed.");
        setMessage(`Verification status: ${body.verification_status}. ${body.provider_result?.message ?? ""}`);
      } else setMessage("Selected documents uploaded. Enter DOB, licence, PAN and Aadhaar to submit a provider verification request.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Verification failed."); }
    finally { setBusy(false); }
  };
  return <form className="stack" onSubmit={submit}>
    <p className="small muted">Company-only identity intake for {driver.name}. Aadhaar/PAN/DL values are sent only to a configured verification provider and are not stored in plaintext by this endpoint.</p>
    <TextField label="Date of birth" type="date" value={dob} onChange={e=>setDob(e.target.value)} />
    <TextField label="Driving licence number" value={license} onChange={e=>setLicense(e.target.value)} />
    <TextField label="PAN number" value={pan} onChange={e=>setPan(e.target.value.toUpperCase())} />
    <TextField label="Aadhaar number" value={aadhaar} onChange={e=>setAadhaar(e.target.value.replace(/\D/g, "").slice(0,12))} />
    {([ ["driving_license", "Driving licence file"], ["pan", "PAN card file"], ["aadhaar", "Aadhaar document file"] ] as const).map(([type,label]) => <label className="field" key={type}><span className="field__label">{label} (PDF/JPG/JPEG/PNG)</span><input className="input" type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={e=>setFiles(old=>({...old,[type]:e.target.files?.[0] ?? null}))} /></label>)}
    {message && <p className="banner banner--info" role="status">{message}</p>}
    <Button type="submit" disabled={busy}>{busy ? "Submitting…" : "Upload documents / verify identity"}</Button>
  </form>;
}

function ContainerCard({
  container,
  drivers,
  onAssign,
  onDelete,
  busy,
}: {
  container: FleetContainer;
  drivers: { id: string; name: string }[];
  onAssign: (driverId: string | null) => void;
  onDelete: () => void;
  busy: boolean;
}) {
  return (
    <article className="card stack">
      <div className="row-between">
        <div>
          <h3>{container.registration_number}</h3>
          <p className="small muted">
            {container.truck.vehicle_class} · {container.truck.body_type} ·{" "}
            {container.truck.max_payload_kg.toLocaleString("en-IN")} kg max payload
          </p>
        </div>
        <Button small variant="danger" disabled={busy} onClick={onDelete}>Remove</Button>
      </div>
      <SelectField
        label={`Driver for ${container.registration_number}`}
        value={container.driver_id ?? ""}
        onChange={(event) => onAssign(event.target.value || null)}
      >
        <option value="">No driver assigned</option>
        {drivers.map((driver) => <option key={driver.id} value={driver.id}>{driver.name}</option>)}
      </SelectField>
    </article>
  );
}

export function FleetPage() {
  usePageTitle("Organization fleet");
  const { user, token } = useAuth();
  const { state } = useWorkspace();
  const driversQuery = useFleetDrivers();
  const containersQuery = useFleetContainers();
  const shipmentsQuery = useShipments();
  const addDriver = useAddFleetDriver();
  const deleteDriver = useDeleteFleetDriver();
  const addContainer = useAddFleetContainer();
  const updateContainer = useUpdateFleetContainer();
  const deleteContainer = useDeleteFleetContainer();
  const drivers = driversQuery.data ?? [];
  const containers = containersQuery.data ?? [];
  const shipments = shipmentsQuery.data ?? [];
  const activeShipments = shipments.filter((shipment) => isActive(shipment.status));
  const unassignedShipments = activeShipments.filter((shipment) => !shipment.assigned_driver_id);

  const [driverName, setDriverName] = useState("");
  const [driverEmail, setDriverEmail] = useState("");
  const [driverLicense, setDriverLicense] = useState("");
  const [driverDob, setDriverDob] = useState("");
  const [driverAddress, setDriverAddress] = useState("");
  const [vehicleName, setVehicleName] = useState("");
  const [minPayload, setMinPayload] = useState("");
  const [vehicleGvw, setVehicleGvw] = useState("");
  const [vehicleLength, setVehicleLength] = useState("");
  const [vehicleWidth, setVehicleWidth] = useState("");
  const [vehicleHeight, setVehicleHeight] = useState("");
  const [axleCount, setAxleCount] = useState("");
  const [rcFile, setRcFile] = useState<File | null>(null);
  const [transportPermitFile, setTransportPermitFile] = useState<File | null>(null);
  const [transportPermitExpiry, setTransportPermitExpiry] = useState("");
  const [transportPermitRoute, setTransportPermitRoute] = useState("");
  const [odcPermitFile, setOdcPermitFile] = useState<File | null>(null);
  const [odcPermitExpiry, setOdcPermitExpiry] = useState("");
  const [odcPermitRoute, setOdcPermitRoute] = useState("");
  const [vehicleForm, setVehicleForm] = useState<"rigid" | "semi_articulated">("rigid");
  const [typeApprovedGvw, setTypeApprovedGvw] = useState("");
  const [tyreCapacityGvw, setTyreCapacityGvw] = useState("");
  const [axleGroupsJson, setAxleGroupsJson] = useState('[{"kind":"single_2_tyres","count":1},{"kind":"tandem_rigid","count":1}]');
  const [pneumaticSuspension, setPneumaticSuspension] = useState(false);
  const [permittedStatesText, setPermittedStatesText] = useState("");
  const [restrictedCitiesText, setRestrictedCitiesText] = useState("");
  const [cityWindowsJson, setCityWindowsJson] = useState("[]");
  const [registrationNumber, setRegistrationNumber] = useState("");
  const [containerDriver, setContainerDriver] = useState("");

  const submitDriver = (event: FormEvent) => {
    event.preventDefault();
    addDriver.mutate(
      { name: driverName, email: driverEmail, license_number: driverLicense || null, date_of_birth: driverDob || null, address: driverAddress || null },
      { onSuccess: () => { setDriverName(""); setDriverEmail(""); setDriverLicense(""); setDriverDob(""); setDriverAddress(""); } },
    );
  };

  const submitContainer = (event: FormEvent) => {
    event.preventDefault();
    let axleGroups: {kind:string;count:number}[];
    try { axleGroups = JSON.parse(axleGroupsJson); if (!Array.isArray(axleGroups)) throw new Error(); }
    catch { window.alert("Axle groups must be valid JSON, for example [{\"kind\":\"single_2_tyres\",\"count\":2}]."); return; }
    let cityWindows: Record<string, unknown>[];
    try { cityWindows = JSON.parse(cityWindowsJson); if (!Array.isArray(cityWindows)) throw new Error(); }
    catch { window.alert("City access windows must be a valid JSON array."); return; }
    addContainer.mutate(
      {
        registration_number: registrationNumber,
        truck: { ...state.truck, vehicle_form: vehicleForm, axle_groups: axleGroups,
          type_approved_gvw_kg: typeApprovedGvw ? Number(typeApprovedGvw) : null,
          tyre_capacity_gvw_kg: tyreCapacityGvw ? Number(tyreCapacityGvw) : null,
          pneumatic_suspension: pneumaticSuspension,
          permitted_states: permittedStatesText.split(",").map(x=>x.trim()).filter(Boolean),
          restricted_cities: restrictedCitiesText.split(",").map(x=>x.trim()).filter(Boolean),
          city_access_windows: cityWindows,
          vehicle_name: vehicleName || null,
          min_payload_kg: minPayload ? Number(minPayload) : null,
          vehicle_gvw_kg: vehicleGvw ? Number(vehicleGvw) : null,
          length_m: vehicleLength ? Number(vehicleLength) : null,
          width_m: vehicleWidth ? Number(vehicleWidth) : null,
          height_m: vehicleHeight ? Number(vehicleHeight) : null,
          axle_count: axleCount ? Number(axleCount) : null },
        driver_id: containerDriver || null,
      },
      { onSuccess: async (created) => {
        const upload = async (kind: string, file: File | null) => { if (!file || !token) return; const fd = new FormData(); fd.append("file", file); const r = await fetch(`/api/documents/vehicles/${created.id}/${kind}`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd }); const d = await r.json(); if (!r.ok) throw new Error(d.detail || `Could not upload ${kind}.`); };
        await upload("rc", rcFile); await upload("transport_permit", transportPermitFile); await upload("over_dimensional_permit", odcPermitFile);
        const savePermit = async (kind: string, expiry: string, route: string) => { if (!expiry && !route) return; const r = await fetch(`/api/fleet/containers/${created.id}/permit-metadata`, { method: "PUT", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ kind, expiry_date: expiry, permitted_route: route }) }); const d = await r.json(); if (!r.ok) throw new Error(d.detail || `Could not save ${kind} details.`); };
        await savePermit("transport_permit", transportPermitExpiry, transportPermitRoute); await savePermit("over_dimensional_permit", odcPermitExpiry, odcPermitRoute);
        setRegistrationNumber(""); setContainerDriver(""); setVehicleName(""); setMinPayload(""); setVehicleGvw(""); setVehicleLength(""); setVehicleWidth(""); setVehicleHeight(""); setAxleCount(""); setRcFile(null); setTransportPermitFile(null); setOdcPermitFile(null); setTransportPermitExpiry(""); setTransportPermitRoute(""); setOdcPermitExpiry(""); setOdcPermitRoute(""); setTypeApprovedGvw(""); setTyreCapacityGvw(""); setAxleGroupsJson("[]"); setPneumaticSuspension(false); setPermittedStatesText(""); setRestrictedCitiesText(""); setCityWindowsJson("[]");
      } },
    );
  };

  const updateDriver = (container: FleetContainer, driverId: string | null) => {
    updateContainer.mutate({
      id: container.id,
      input: { registration_number: container.registration_number, truck: container.truck, driver_id: driverId },
    });
  };

  const assignmentFor = (shipmentId: string) => {
    const shipment = shipments.find((item) => item.id === shipmentId);
    if (!shipment?.assigned_driver_id) return "Unassigned";
    const driver = drivers.find((item) => item.id === shipment.assigned_driver_id);
    const container = containers.find((item) => item.id === shipment.fleet_container_id);
    return `${driver?.name ?? "Driver"} · ${container?.registration_number ?? "Container"}`;
  };

  return (
    <div className="fleet-page stack-lg">
      <section className="fleet-hero" aria-labelledby="fleet-heading">
        <div className="fleet-hero__intro">
          <span className="badge badge--info">Organization owner</span>
          <h1 id="fleet-heading">{user?.organization_name ?? "Fleet operations"}</h1>
          <p>One place to manage drivers, containers, and accepted offers across your organization.</p>
          <ButtonLink to="/workspace" variant="primary">Find client offers</ButtonLink>
        </div>
        <dl className="fleet-stats" aria-label="Fleet overview">
          <div><dt>Drivers</dt><dd>{drivers.length}</dd></div>
          <div><dt>Containers</dt><dd>{containers.length}</dd></div>
          <div><dt>Active offers</dt><dd>{activeShipments.length}</dd></div>
          <div><dt>Need assignment</dt><dd>{unassignedShipments.length}</dd></div>
        </dl>
      </section>

      <p className="field__hint">
        Fleet assignments are managed here; live vehicle location and telemetry are not connected.
      </p>

      <div className="detail-grid">
        <Card title="Drivers">
          <div className="stack">
            <form className="stack" onSubmit={submitDriver}>
              <TextField label="Driver name" value={driverName} onChange={(event) => setDriverName(event.target.value)} />
              <TextField label="Driver email" type="email" value={driverEmail} onChange={(event) => setDriverEmail(event.target.value)} />
              <TextField label="Driving licence number" value={driverLicense} onChange={e=>setDriverLicense(e.target.value)} />
              <TextField label="Date of birth" type="date" value={driverDob} onChange={e=>setDriverDob(e.target.value)} />
              <TextField label="Address" value={driverAddress} onChange={e=>setDriverAddress(e.target.value)} />
              {errorText(addDriver.error) && <p className="form-error" role="alert">{errorText(addDriver.error)}</p>}
              <Button type="submit" variant="primary" disabled={addDriver.isPending}>
                {addDriver.isPending ? "Adding…" : "Add driver"}
              </Button>
            </form>
            <p className="field__hint">This adds a company fleet roster record. Government identity checks remain pending until an authorized verification provider is configured.</p>
            {driversQuery.isError && <p className="form-error" role="alert">Could not load drivers: {errorText(driversQuery.error)}</p>}
            {drivers.length === 0 && !driversQuery.isLoading ? (
              <EmptyState title="No drivers yet">Add drivers to assign containers and accepted offers.</EmptyState>
            ) : (
              <ul className="stack" style={{ listStyle: "none", padding: 0 }}>
                {drivers.map((driver) => (
                  <li className="row-between" key={driver.id}>
                    <span><strong>{driver.name}</strong><br /><span className="small muted">{driver.email} · {driver.verification_status ?? "not submitted"}{driver.blacklisted ? " · BLACKLISTED" : ""}</span></span>
                    <Button
                      small
                      variant="danger"
                      disabled={deleteDriver.isPending}
                      onClick={() => deleteDriver.mutate(driver.id)}
                    >
                      Remove
                    </Button>
                  </li>
                ))}
              </ul>
            )}
            {drivers.map(driver => <details key={`${driver.id}-verification`} className="stack"><summary>Identity documents and verification — {driver.name}</summary><DriverVerification driver={driver} token={token} /></details>)}
            {errorText(deleteDriver.error) && <p className="form-error" role="alert">{errorText(deleteDriver.error)}</p>}
          </div>
        </Card>

        <Card title="Containers">
          <div className="stack">
            <p className="small muted">
              Company-entered vehicle details are used for fleet records and matching. Add the registration number separately from the RC document.{" "}
              <Link to="/workspace">Review truck specifications</Link>.
            </p>
            <p className="small">
              <a href="https://ldb.co.in/ldb/containersearch" target="_blank" rel="noopener noreferrer">
                Search or track a container with LDB
              </a>
            </p>
            <form className="stack" onSubmit={submitContainer}>
              <TextField label="Vehicle name / model" value={vehicleName} onChange={e=>setVehicleName(e.target.value)} />
              <div className="grid-2">
                <TextField label="Minimum load (kg)" type="number" min={0} value={minPayload} onChange={e=>setMinPayload(e.target.value)} />
                <TextField label="Maximum payload (kg)" type="number" min={1} value={String(state.truck.max_payload_kg)} disabled />
                <TextField label="Registered vehicle GVW (kg)" type="number" min={1} value={vehicleGvw} onChange={e=>setVehicleGvw(e.target.value)} />
                <TextField label="Length (m)" type="number" min={0} step="0.01" value={vehicleLength} onChange={e=>setVehicleLength(e.target.value)} />
                <TextField label="Width (m)" type="number" min={0} step="0.01" value={vehicleWidth} onChange={e=>setVehicleWidth(e.target.value)} />
                <TextField label="Height (m)" type="number" min={0} step="0.01" value={vehicleHeight} onChange={e=>setVehicleHeight(e.target.value)} />
                <TextField label="Axle count" type="number" min={2} max={20} value={axleCount} onChange={e=>setAxleCount(e.target.value)} />
                <SelectField label="Vehicle form for GVW cap" value={vehicleForm} onChange={e=>setVehicleForm(e.target.value as "rigid" | "semi_articulated")}><option value="rigid">Rigid vehicle</option><option value="semi_articulated">Semi-articulated / truck-trailer</option></SelectField>
                <TextField label="Type-approved GVW (kg, from RC/type approval)" type="number" min={1} value={typeApprovedGvw} onChange={e=>setTypeApprovedGvw(e.target.value)} />
                <TextField label="Total tyre load capacity (kg)" type="number" min={1} value={tyreCapacityGvw} onChange={e=>setTyreCapacityGvw(e.target.value)} />
              </div>
              <TextAreaField label="Axle group configuration (JSON)" value={axleGroupsJson} onChange={e=>setAxleGroupsJson(e.target.value)} hint='Kinds: single_1_tyre, single_2_tyres, single_4_tyres, tandem_rigid, tandem_puller, tridem_rigid, modular_axle_row. Count is the number of such groups.' />
              <label className="row" style={{alignItems:"center",gap:"0.5rem"}}><input type="checkbox" checked={pneumaticSuspension} onChange={e=>setPneumaticSuspension(e.target.checked)} /> Pneumatic suspension (confirm from vehicle documents)</label>
              <TextField label="Permitted states (comma-separated, company-entered)" value={permittedStatesText} onChange={e=>setPermittedStatesText(e.target.value)} />
              <TextField label="Restricted cities (comma-separated, company-entered)" value={restrictedCitiesText} onChange={e=>setRestrictedCitiesText(e.target.value)} />
              <TextAreaField label="City entry windows (JSON, local authority schedule)" value={cityWindowsJson} onChange={e=>setCityWindowsJson(e.target.value)} hint='Example: [{"city":"Mumbai","allowed_from":"22:00","allowed_until":"06:00","days":["Mon","Tue"]}]. These are stored company inputs, not live verified city rules.' />
              <TextField
                label="Vehicle registration number (number plate)"
                value={registrationNumber}
                onChange={(event) => setRegistrationNumber(event.target.value)}
              />
              <label className="field"><span className="field__label">Registration Certificate (RC) — PDF/JPG/JPEG/PNG</span><input className="input" type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={e=>setRcFile(e.target.files?.[0] ?? null)} /></label>
              <h3>Transport permit</h3>
              <label className="field"><span className="field__label">Permit file — PDF/JPG/JPEG/PNG</span><input className="input" type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={e=>setTransportPermitFile(e.target.files?.[0] ?? null)} /></label>
              <div className="grid-2"><TextField label="Permit expiry date" type="date" value={transportPermitExpiry} onChange={e=>setTransportPermitExpiry(e.target.value)} /><TextField label="Permitted route" value={transportPermitRoute} onChange={e=>setTransportPermitRoute(e.target.value)} /></div>
              <h3>Over-dimensional cargo permit (if applicable)</h3>
              <label className="field"><span className="field__label">ODC permit file — PDF/JPG/JPEG/PNG</span><input className="input" type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={e=>setOdcPermitFile(e.target.files?.[0] ?? null)} /></label>
              <div className="grid-2"><TextField label="ODC permit expiry date" type="date" value={odcPermitExpiry} onChange={e=>setOdcPermitExpiry(e.target.value)} /><TextField label="ODC permitted route" value={odcPermitRoute} onChange={e=>setOdcPermitRoute(e.target.value)} /></div>
              <SelectField label="Assigned driver" value={containerDriver} onChange={(event) => setContainerDriver(event.target.value)}>
                <option value="">No driver assigned</option>
                {drivers.map((driver) => <option key={driver.id} value={driver.id}>{driver.name}</option>)}
              </SelectField>
              {errorText(addContainer.error) && <p className="form-error" role="alert">{errorText(addContainer.error)}</p>}
              <Button type="submit" variant="primary" disabled={addContainer.isPending}>
                {addContainer.isPending ? "Adding…" : "Register container"}
              </Button>
            </form>
            {containersQuery.isError && <p className="form-error" role="alert">Could not load containers: {errorText(containersQuery.error)}</p>}
            {containers.length === 0 && !containersQuery.isLoading ? (
              <EmptyState title="No containers yet">Register a container to use its specifications when matching offers.</EmptyState>
            ) : (
              <div className="stack">
                {containers.map((container) => (
                  <ContainerCard
                    key={container.id}
                    container={container}
                    drivers={drivers}
                    busy={updateContainer.isPending || deleteContainer.isPending}
                    onAssign={(driverId) => updateDriver(container, driverId)}
                    onDelete={() => deleteContainer.mutate(container.id)}
                  />
                ))}
              </div>
            )}
            {errorText(updateContainer.error) && <p className="form-error" role="alert">{errorText(updateContainer.error)}</p>}
            {errorText(deleteContainer.error) && <p className="form-error" role="alert">{errorText(deleteContainer.error)}</p>}
          </div>
        </Card>
      </div>

      {containers.length > 0 && (
        <Card title="Fleet location overview">
          <div className="stack">
            <MapView
              fit={containers.map((container) => container.truck.location)}
              label="Saved fleet container locations"
              height="24rem"
            >
              {containers.map((container) => (
                <CircleMarker
                  key={container.id}
                  center={[container.truck.location.lat, container.truck.location.lng]}
                  radius={8}
                  pathOptions={{ color: "#ffffff", fillColor: "#167d80", fillOpacity: 1, weight: 3 }}
                >
                  <Tooltip>
                    {container.registration_number}
                    {container.driver_id
                      ? ` · ${drivers.find((driver) => driver.id === container.driver_id)?.name ?? "Assigned driver"}`
                      : " · Unassigned"}
                  </Tooltip>
                </CircleMarker>
              ))}
            </MapView>
            <p className="field__hint">Map positions are saved truck locations, not live tracking data.</p>
          </div>
        </Card>
      )}

      <Card title="Accepted offers">
        {shipmentsQuery.isError && <p className="form-error" role="alert">Could not load accepted offers: {errorText(shipmentsQuery.error)}</p>}
        {shipments.length === 0 ? (
          <EmptyState title="No accepted offers yet">
            Search client offers and accept a suitable job. You can assign it to a driver and container from the shipment page.
          </EmptyState>
        ) : (
          <div className="table-scroll">
            <table className="table">
              <caption className="sr-only">Accepted offers and fleet assignments</caption>
              <thead>
                <tr><th scope="col">Offer</th><th scope="col">Status</th><th scope="col">Assignment</th><th scope="col">Route</th></tr>
              </thead>
              <tbody>
                {shipments.map((shipment) => (
                  <tr key={shipment.id}>
                    <td><Link to={`/shipments/${shipment.id}`}>{shipment.candidate.title}</Link></td>
                    <td>{STATUS_LABEL[shipment.status]}</td>
                    <td>{assignmentFor(shipment.id)}</td>
                    <td>{shipment.route_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
