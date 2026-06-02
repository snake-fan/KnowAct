import { FormEvent, useEffect, useRef, useState } from "react";
import {
  ApiRequestError,
  CandidateProfileContext,
  ProfileContextCandidateResponse,
  ProfileContextConfirmationResponse,
  confirmProfileContextCandidate,
  generateProfileContextCandidate,
  listBenchmarkDomains,
  saveProfileContextCandidate
} from "../../api/authoring";

type ClientProvider = "openai" | "deepseek";
type ListField = "background" | "prior_experience" | "goals" | "preferences";

export function UserProfileWorkbench() {
  const [benchmarkDomains, setBenchmarkDomains] = useState<string[]>([]);
  const [benchmarkDomain, setBenchmarkDomain] = useState("");
  const [roughDescription, setRoughDescription] = useState("");
  const [domainSummary, setDomainSummary] = useState("");
  const [clientProvider, setClientProvider] = useState<ClientProvider>("openai");
  const [candidate, setCandidate] = useState<ProfileContextCandidateResponse | null>(null);
  const [draft, setDraft] = useState<CandidateProfileContext | null>(null);
  const [confirmed, setConfirmed] = useState<ProfileContextConfirmationResponse | null>(null);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [userId, setUserId] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reviewStageRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    void refreshBenchmarkDomains();
  }, []);

  async function refreshBenchmarkDomains() {
    await runTask("domains", async () => {
      const domains = await listBenchmarkDomains();
      setBenchmarkDomains(domains);
      setBenchmarkDomain((current) => current || domains[0] || "");
    });
  }

  async function handleGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!benchmarkDomain) {
      setError("Select a benchmark domain first.");
      return;
    }
    if (!roughDescription.trim()) {
      setError("Describe the synthetic user before generating a profile.");
      return;
    }

    await runTask("generate profile", async () => {
      const response = await generateProfileContextCandidate({
        benchmarkDomain,
        roughDescription: roughDescription.trim(),
        domainSummary: domainSummary.trim() || undefined,
        clientProvider
      });
      setCandidate(response);
      setDraft(response.candidate_profile_context);
      setConfirmed(null);
      setUserId("");
      setNotice(`Generated profile draft ${response.run_id}. Review and edit it before confirmation.`);
      requestAnimationFrame(() => {
        reviewStageRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  async function handleSave() {
    if (!candidate || !draft || confirmed) return;
    await runTask("save profile", async () => {
      const response = await saveProfileContextCandidate(candidate.run_id, draft);
      setCandidate(response);
      setDraft(response.candidate_profile_context);
      setNotice("Profile Context draft saved.");
    });
  }

  function openConfirmDialog() {
    if (!candidate || !draft || confirmed) return;
    setError(null);
    setUserId("");
    setConfirmDialogOpen(true);
  }

  async function handleConfirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!candidate || !draft) return;
    const trimmedUserId = userId.trim();
    if (!trimmedUserId) {
      setError("User ID is required.");
      return;
    }

    await runTask("confirm profile", async () => {
      const saved = await saveProfileContextCandidate(candidate.run_id, draft);
      setCandidate(saved);
      setDraft(saved.candidate_profile_context);
      let confirmation: ProfileContextConfirmationResponse;
      try {
        confirmation = await confirmProfileContextCandidate(
          saved.run_id,
          saved.candidate_profile_context.benchmark_domain,
          trimmedUserId
        );
      } catch (taskError) {
        if (!(taskError instanceof ApiRequestError) || taskError.status !== 409) {
          throw taskError;
        }
        throw new Error(
          `User ID "${trimmedUserId}" is unavailable or this draft was already confirmed. Choose a new user ID or generate a new draft.`
        );
      }
      setConfirmed(confirmation);
      setConfirmDialogOpen(false);
      setNotice(`Published immutable Profile Context for ${confirmation.profile_context.user_id}.`);
    });
  }

  async function runTask(label: string, task: () => Promise<void>) {
    setBusy(label);
    setError(null);
    setNotice(null);
    try {
      await task();
    } catch (taskError) {
      setError(taskError instanceof Error ? taskError.message : String(taskError));
    } finally {
      setBusy(null);
    }
  }

  function updateDraft(patch: Partial<CandidateProfileContext>) {
    if (!draft || confirmed) return;
    setDraft({ ...draft, ...patch });
  }

  function updateList(field: ListField, items: string[]) {
    updateDraft({ [field]: items });
  }

  return (
    <main className="profile-workbench">
      <section className="topbar profile-topbar">
        <div>
          <p className="eyebrow">Profile Context Authoring</p>
          <h1>User Profile</h1>
          <p>Expand a rough synthetic-user description into a reviewable Profile Context, edit the draft, then publish one immutable snapshot.</p>
        </div>
        <div className="status-strip" aria-live="polite">
          {busy && <span className="status busy">Working: {busy}</span>}
          {notice && <span className="status ok">{notice}</span>}
          {error && <span className="status error">{error}</span>}
        </div>
      </section>

      <div className="profile-scroll">
        <section className="profile-composer-stage">
          <form className="profile-composer-card" onSubmit={handleGenerate}>
            <div className="profile-card-heading">
              <p className="eyebrow">New Synthetic User</p>
              <h2>Describe the person you want to model</h2>
              <p>Keep this at the person level. Knowledge-state details are generated later from the confirmed profile.</p>
            </div>

            <label>
              Benchmark Domain
              <select
                value={benchmarkDomain}
                onChange={(event) => setBenchmarkDomain(event.target.value)}
                disabled={busy !== null}
                required
              >
                <option value="">Select a benchmark domain</option>
                {benchmarkDomains.map((domain) => (
                  <option key={domain} value={domain}>{domain}</option>
                ))}
              </select>
            </label>

            <label>
              Rough Description
              <textarea
                className="rough-description-input"
                value={roughDescription}
                onChange={(event) => setRoughDescription(event.target.value)}
                placeholder="Example: A practical beginner who can follow sklearn examples but has weak statistical foundations."
                disabled={busy !== null}
                required
              />
            </label>

            <label>
              <span className="label-with-hint">
                Domain Summary
                <span>Optional</span>
              </span>
              <textarea
                value={domainSummary}
                onChange={(event) => setDomainSummary(event.target.value)}
                placeholder="Add a short subject-area summary when the domain name alone is not enough context."
                disabled={busy !== null}
              />
            </label>

            <div className="profile-composer-actions">
              <label className="provider-picker">
                <span>Model provider</span>
                <select
                  value={clientProvider}
                  onChange={(event) => setClientProvider(event.target.value as ClientProvider)}
                  disabled={busy !== null}
                >
                  <option value="openai">OpenAI</option>
                  <option value="deepseek">DeepSeek</option>
                </select>
              </label>
              <button type="submit" className="send-button" disabled={busy !== null || !benchmarkDomain}>
                Generate Profile
                <span aria-hidden="true">&#8593;</span>
              </button>
            </div>
          </form>
        </section>

        {candidate && draft && (
          <section className="profile-review-stage" ref={reviewStageRef}>
            <div className="profile-review-shell">
              <div className="profile-review-header">
                <div>
                  <p className="eyebrow">Structured Profile Context</p>
                  <h2>{confirmed ? "Confirmed synthetic user snapshot" : "Review generated draft"}</h2>
                  <p>
                    {confirmed
                      ? "This snapshot is immutable. Scroll upward to generate another draft."
                      : "Edit the structured fields, save the draft, then assign a formal user ID at confirmation."}
                  </p>
                </div>
                <span className={confirmed ? "lifecycle-badge confirmed" : "lifecycle-badge"}>
                  {confirmed ? "Confirmed" : "Candidate"}
                </span>
              </div>

              <div className="profile-meta-grid">
                <Meta label="Benchmark domain" value={draft.benchmark_domain} />
                <Meta label="Candidate run" value={candidate.run_id} />
                {confirmed && <Meta label="User ID" value={confirmed.profile_context.user_id} />}
              </div>

              <div className="profile-fields">
                <label className="profile-summary-field">
                  Summary
                  <textarea
                    value={draft.summary}
                    onChange={(event) => updateDraft({ summary: event.target.value })}
                    disabled={Boolean(confirmed)}
                  />
                </label>

                <ProfileListEditor
                  title="Background"
                  description="At least one background fact is required."
                  items={draft.background}
                  onChange={(items) => updateList("background", items)}
                  disabled={Boolean(confirmed)}
                />
                <ProfileListEditor
                  title="Prior Experience"
                  description="Optional prior exposure, tools, or workflows."
                  items={draft.prior_experience}
                  onChange={(items) => updateList("prior_experience", items)}
                  disabled={Boolean(confirmed)}
                />
                <ProfileListEditor
                  title="Goals"
                  description="At least one concrete goal is required."
                  items={draft.goals}
                  onChange={(items) => updateList("goals", items)}
                  disabled={Boolean(confirmed)}
                />
                <ProfileListEditor
                  title="Preferences"
                  description="Optional interaction or learning preferences."
                  items={draft.preferences}
                  onChange={(items) => updateList("preferences", items)}
                  disabled={Boolean(confirmed)}
                />
              </div>

              <div className="profile-review-actions">
                <div>
                  {confirmed ? (
                    <p className="published-path">Published: {confirmed.artifact_paths.profile_context_uri}</p>
                  ) : (
                    <p>Confirmation publishes a lightweight immutable snapshot. Later edits require a new candidate run and user ID.</p>
                  )}
                </div>
                {!confirmed && (
                  <div className="button-row">
                    <button type="button" className="secondary" onClick={handleSave} disabled={busy !== null}>Save Draft</button>
                    <button type="button" onClick={openConfirmDialog} disabled={busy !== null}>Confirm Profile</button>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}
      </div>

      {confirmDialogOpen && candidate && draft && (
        <div className="dialog-backdrop">
          <form className="dialog" onSubmit={handleConfirm}>
            <h2>Confirm Profile Context</h2>
            <p>Save the current edits and publish them as one immutable synthetic-user snapshot.</p>
            <label>
              User ID
              <input
                autoFocus
                value={userId}
                onChange={(event) => setUserId(event.target.value)}
                placeholder="synthetic_user_001"
                pattern="[A-Za-z0-9][A-Za-z0-9_.-]{0,127}"
                required
              />
            </label>
            <div className="button-row dialog-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => setConfirmDialogOpen(false)}
                disabled={busy !== null}
              >
                Cancel
              </button>
              <button type="submit" disabled={busy !== null}>Publish Snapshot</button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}

function ProfileListEditor({
  title,
  description,
  items,
  onChange,
  disabled
}: {
  title: string;
  description: string;
  items: string[];
  onChange: (items: string[]) => void;
  disabled: boolean;
}) {
  return (
    <section className="profile-list-field">
      <div className="profile-list-heading">
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
        {!disabled && (
          <button type="button" className="compact-button secondary" onClick={() => onChange([...items, ""])}>
            Add item
          </button>
        )}
      </div>
      {items.length === 0 ? (
        <p className="empty">No items.</p>
      ) : (
        <div className="profile-list-items">
          {items.map((item, index) => (
            <div className="profile-list-row" key={`${title}-${index}`}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <textarea
                value={item}
                onChange={(event) => {
                  const nextItems = [...items];
                  nextItems[index] = event.target.value;
                  onChange(nextItems);
                }}
                disabled={disabled}
              />
              {!disabled && (
                <button
                  type="button"
                  className="remove-item-button"
                  aria-label={`Remove ${title} item ${index + 1}`}
                  onClick={() => onChange(items.filter((_value, itemIndex) => itemIndex !== index))}
                >
                  &#215;
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="profile-meta">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
