import { useEffect, useMemo, useState } from "react";

const apiUrl = import.meta.env.VITE_API_URL || "";

type IndianCollege = {
  id: string;
  name: string;
  short_name: string;
  category: string;
  state: string;
  city: string;
  domain: string;
  admissions_portal: string;
  entrance_exams: string[];
  counseling_body: string;
  country: string;
};

type Requirement = {
  id: string;
  title: string;
  description: string;
  required: boolean;
  document_type: string;
  check: string;
  value?: number;
  source_url: string;
  source_category: "official" | "government" | "community";
  source_name: string;
};

type SourceFound = {
  category: string;
  name: string;
  url: string;
  badge_color: string;
};

type Checklist = {
  requirement_set_id: string;
  university_name: string;
  university_domain: string;
  application_type: string;
  college_category: string;
  counseling_body?: string;
  requirements: Requirement[];
  disclaimer: string;
  sources_found?: SourceFound[];
};

type Result = {
  rule_id: string;
  title: string;
  status: "passed" | "failed" | "warning";
  message: string;
  evidence?: string;
  source_url?: string;
  source_category?: string;
  source_name?: string;
};

type Verification = {
  verification_id: string;
  applicant_name: string;
  readiness_score: number;
  university_name: string;
  application_type: string;
  results: Result[];
  suggestions: string[];
  report_url: string;
  audit_trail: string[];
};

export default function App() {
  const [colleges, setColleges] = useState<IndianCollege[]>([]);
  const [states, setStates] = useState<string[]>([]);
  const [categories, setCategories] = useState<string[]>([]);

  const [selectedState, setSelectedState] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const [selectedCollege, setSelectedCollege] = useState<IndianCollege | null>(null);
  const [applicantName, setApplicantName] = useState("Ryan Jain");
  const [applicationType, setApplicationType] = useState("undergraduate");

  const [checklist, setChecklist] = useState<Checklist | null>(null);
  const [files, setFiles] = useState<Record<string, File>>({});
  const [result, setResult] = useState<Verification | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState("");
  const [error, setError] = useState("");

  // Load initial colleges catalog, states and categories
  useEffect(() => {
    async function loadInitialData() {
      try {
        const [collegesRes, statesRes, catsRes] = await Promise.all([
          fetch(`${apiUrl}/api/v1/colleges`),
          fetch(`${apiUrl}/api/v1/colleges/states`),
          fetch(`${apiUrl}/api/v1/colleges/categories`),
        ]);

        if (collegesRes.ok) {
          const list = await collegesRes.json();
          setColleges(list);
          const vit = list.find((c: IndianCollege) => c.id.includes("vit_vellore"));
          if (vit) {
            setSelectedCollege(vit);
            setSearchQuery(vit.name);
          }
        }
        if (statesRes.ok) setStates(await statesRes.json());
        if (catsRes.ok) setCategories(await catsRes.json());
      } catch (err) {
        console.error("Error loading colleges data", err);
      }
    }
    loadInitialData();
  }, []);

  // Filtered colleges list for searchable dropdown
  const filteredColleges = useMemo(() => {
    return colleges.filter((c) => {
      if (selectedState !== "all" && c.state.toLowerCase() !== selectedState.toLowerCase()) {
        return false;
      }
      if (selectedCategory !== "all" && c.category.toLowerCase() !== selectedCategory.toLowerCase()) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const text = `${c.name} ${c.short_name} ${c.city} ${c.state} ${c.domain} ${c.category} ${c.entrance_exams.join(" ")} ${c.counseling_body}`.toLowerCase();
        return text.includes(q);
      }
      return true;
    });
  }, [colleges, selectedState, selectedCategory, searchQuery]);

  async function handleSelectCollege(college: IndianCollege) {
    setSelectedCollege(college);
    setSearchQuery(college.name);
    setIsDropdownOpen(false);
    setChecklist(null);
    setResult(null);
    setFiles({});
    setError("");
  }

  async function loadMultiSourceRequirements() {
    if (!selectedCollege && !searchQuery.trim()) {
      setError("Please select an Indian engineering college from the list.");
      return;
    }

    const collegeName = selectedCollege ? selectedCollege.name : searchQuery.trim();
    const collegeDomain = selectedCollege ? selectedCollege.domain : "vit.ac.in";

    setLoading(true);
    setLoadingStep("Probing Official Portal, JoSAA/AICTE Guidelines & Quora Community Sources…");
    setError("");
    setChecklist(null);
    setResult(null);
    setFiles({});

    try {
      const data = new FormData();
      data.append("university_name", collegeName);
      data.append("university_domain", collegeDomain);
      data.append("application_type", applicationType);

      const response = await fetch(`${apiUrl}/api/v1/requirements`, {
        method: "POST",
        body: data,
      });

      if (!response.ok) {
        let errMessage = "Could not retrieve requirements.";
        try {
          const body = await response.json();
          errMessage = body.detail || errMessage;
        } catch {
          const text = await response.text();
          if (text) errMessage = text;
        }
        throw new Error(errMessage);
      }

      const body = await response.json();
      setChecklist(body);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Failed to load multi-source requirements.");
    } finally {
      setLoading(false);
      setLoadingStep("");
    }
  }

  function handleFileChange(reqId: string, file: File | null) {
    setFiles((prev) => {
      const next = { ...prev };
      if (file) {
        next[reqId] = file;
      } else {
        delete next[reqId];
      }
      return next;
    });
  }

  async function submitVerification() {
    if (!checklist) return;
    if (!applicantName.trim()) {
      setError("Please enter the candidate's full name.");
      return;
    }

    const missingRequired = checklist.requirements.filter(
      (item) => item.required && !files[item.id]
    );

    if (missingRequired.length > 0) {
      setError(
        `Please upload all mandatory documents before verification: ${missingRequired
          .map((item) => item.title)
          .join(", ")}`
      );
      return;
    }

    setLoading(true);
    setLoadingStep("Running Multi-Agent OCR & Document Verification System…");
    setError("");
    setResult(null);

    try {
      const data = new FormData();
      data.append("applicant_name", applicantName.trim());
      data.append("requirement_set_id", checklist.requirement_set_id);

      checklist.requirements.forEach((item) => {
        const file = files[item.id];
        if (file) {
          data.append("documents", file);
          data.append("document_types", item.document_type);
        }
      });

      const response = await fetch(`${apiUrl}/api/v1/verifications`, {
        method: "POST",
        body: data,
      });

      if (!response.ok) {
        let errMessage = "Verification failed.";
        try {
          const body = await response.json();
          errMessage = body.detail || errMessage;
        } catch {
          const text = await response.text();
          if (text) errMessage = text;
        }
        throw new Error(errMessage);
      }

      const body = await response.json();
      setResult(body);
      setTimeout(() => {
        document.getElementById("verification-results")?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Verification encountered an error.");
    } finally {
      setLoading(false);
      setLoadingStep("");
    }
  }

  const uploadedCount = Object.keys(files).length;
  const totalReqCount = checklist?.requirements.length || 0;
  const mandatoryCount = checklist?.requirements.filter((r) => r.required).length || 0;

  return (
    <div className="app-container">
      {/* Header */}
      <header className="site-header">
        <div className="header-inner">
          <div className="brand-group">
            <span className="badge-flag">🇮🇳 INDIA TECH ADMISSIONS</span>
            <h1>Engineering Admissions Verification Assistant</h1>
            <p className="subtitle">
              Multi-Source Document Discovery & Automated Credential Verification for All Engineering Colleges of India
            </p>
          </div>
          <div className="header-stat">
            <span className="stat-num">{colleges.length || "90+"}</span>
            <span className="stat-lbl">Institutions Indexed (IITs · NITs · IIITs · BITS · Deemed · State)</span>
          </div>
        </div>
      </header>

      <main className="main-content">
        {/* Step 1: College Selection & Criteria */}
        <section className="glass-card selection-card">
          <div className="section-header">
            <div className="step-indicator">1</div>
            <div>
              <h2>Select Engineering College & Application Track</h2>
              <p className="text-muted">
                Filter across all Indian engineering institutes or search by college name, city, state, or entrance exam.
              </p>
            </div>
          </div>

          <div className="filters-grid">
            {/* Category Filter */}
            <div className="form-group">
              <label className="field-label">Institution Category</label>
              <select
                className="custom-select"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                <option value="all">All Categories ({colleges.length})</option>
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            {/* State Filter */}
            <div className="form-group">
              <label className="field-label">State / UT</label>
              <select
                className="custom-select"
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
              >
                <option value="all">All States of India</option>
                {states.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            </div>

            {/* Application Type */}
            <div className="form-group">
              <label className="field-label">Admission Stream</label>
              <select
                className="custom-select"
                value={applicationType}
                onChange={(e) => setApplicationType(e.target.value)}
              >
                <option value="undergraduate">B.Tech / B.E. (Undergraduate)</option>
                <option value="postgraduate">M.Tech / M.E. (Postgraduate / GATE)</option>
                <option value="lateral_entry">Lateral Entry (Diploma to 2nd Year B.Tech)</option>
                <option value="international">NRI / DASA / CIWG Quota</option>
                <option value="scholarship">Fee Concession / TFWS / EBC Scheme</option>
              </select>
            </div>
          </div>

          {/* Searchable Combobox */}
          <div className="form-group combobox-container">
            <label className="field-label">
              Search Indian Engineering College Dropdown
              <span className="field-hint">({filteredColleges.length} matches found)</span>
            </label>
            <div className="search-input-wrapper">
              <input
                type="text"
                className="search-input"
                placeholder="Type to search e.g. VIT Vellore, IIT Bombay, BITS Pilani, NIT Trichy, RVCE..."
                value={searchQuery}
                onFocus={() => setIsDropdownOpen(true)}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setIsDropdownOpen(true);
                  if (selectedCollege && selectedCollege.name !== e.target.value) {
                    setSelectedCollege(null);
                  }
                }}
              />
              {searchQuery && (
                <button
                  type="button"
                  className="clear-btn"
                  onClick={() => {
                    setSearchQuery("");
                    setSelectedCollege(null);
                    setIsDropdownOpen(true);
                  }}
                >
                  ✕
                </button>
              )}
            </div>

            {/* Dropdown Menu */}
            {isDropdownOpen && (
              <div className="dropdown-panel">
                <div className="dropdown-header">
                  <span>Select an Engineering College ({filteredColleges.length} available)</span>
                  <button
                    type="button"
                    className="close-dropdown-btn"
                    onClick={() => setIsDropdownOpen(false)}
                  >
                    Done
                  </button>
                </div>
                <div className="dropdown-list">
                  {filteredColleges.length > 0 ? (
                    filteredColleges.map((item) => (
                      <div
                        key={item.id}
                        className={`dropdown-item ${selectedCollege?.id === item.id ? "active" : ""}`}
                        onClick={() => handleSelectCollege(item)}
                      >
                        <div className="item-main">
                          <div className="item-title">{item.name}</div>
                          <div className="item-meta">
                            <span className="pill-category">{item.category}</span>
                            <span className="pill-location">📍 {item.city}, {item.state}</span>
                            <span className="pill-domain">🌐 {item.domain}</span>
                          </div>
                        </div>
                        <div className="item-exams">
                          {item.entrance_exams.slice(0, 2).map((exam) => (
                            <span key={exam} className="pill-exam">{exam}</span>
                          ))}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="dropdown-empty">
                      No engineering colleges match your search. Try adjusting the state or category filter.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Selected College Detail Card */}
          {selectedCollege && (
            <div className="selected-college-box">
              <div className="college-meta-left">
                <div className="college-title-row">
                  <h3>{selectedCollege.name}</h3>
                  <span className="badge-cat">{selectedCollege.category}</span>
                </div>
                <div className="college-details-pills">
                  <span>📍 {selectedCollege.city}, {selectedCollege.state}</span>
                  <span>🏛️ Counseling: <b>{selectedCollege.counseling_body}</b></span>
                  <span>
                    🌐 Portal:{" "}
                    <a href={selectedCollege.admissions_portal} target="_blank" rel="noreferrer">
                      {selectedCollege.domain}
                    </a>
                  </span>
                </div>
              </div>
              <div className="college-exams-tag">
                <span className="exams-label">Entrance Channels:</span>
                <div className="exams-list">
                  {selectedCollege.entrance_exams.map((ex) => (
                    <span key={ex} className="exam-chip">{ex}</span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Applicant Info */}
          <div className="applicant-row">
            <div className="form-group flex-1">
              <label className="field-label">Candidate Full Name</label>
              <input
                type="text"
                className="custom-input"
                placeholder="e.g. Ryan Jain"
                value={applicantName}
                onChange={(e) => setApplicantName(e.target.value)}
              />
            </div>

            <div className="form-group flex-action">
              <button
                type="button"
                className="btn btn-primary btn-discover"
                disabled={loading || (!selectedCollege && !searchQuery.trim())}
                onClick={loadMultiSourceRequirements}
              >
                {loading ? (
                  <>
                    <span className="spinner"></span>
                    <span>Discovering Multi-Source Requirements…</span>
                  </>
                ) : (
                  <>
                    <span>🔍 Discover Required Documents</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {loadingStep && <div className="loading-status-bar">⚡ {loadingStep}</div>}
          {error && <div className="alert-box alert-error">{error}</div>}
        </section>

        {/* Step 2: Multi-Source Requirements Checklist */}
        {checklist && (
          <section className="glass-card requirements-card" id="requirements-section">
            <div className="section-header">
              <div className="step-indicator">2</div>
              <div>
                <h2>Multi-Source Required Documents for {checklist.university_name}</h2>
                <p className="text-muted">
                  Checklist compiled across Official Admissions Portal, Government Guidelines (JoSAA/AICTE/State CET), and Quora Student Reporting Guides.
                </p>
              </div>
            </div>

            {/* Source Discovery Badges */}
            <div className="sources-banner">
              <div className="sources-header">
                <span className="sources-title">Verified Discovery Sources:</span>
              </div>
              <div className="sources-grid">
                {checklist.sources_found && checklist.sources_found.length > 0 ? (
                  checklist.sources_found.map((src, idx) => (
                    <a
                      key={idx}
                      href={src.url}
                      target="_blank"
                      rel="noreferrer"
                      className={`source-card source-${src.badge_color || "official"}`}
                    >
                      <div className="source-type">
                        {src.badge_color === "official"
                          ? "🏛️ Official College Portal"
                          : src.badge_color === "government"
                            ? "🇮🇳 Government Counseling Body"
                            : "👥 Community / Quora Discussions"}
                      </div>
                      <div className="source-name">{src.name}</div>
                      <div className="source-link-text">Visit Source ↗</div>
                    </a>
                  ))
                ) : (
                  <>
                    <div className="source-card source-official">
                      <div className="source-type">🏛️ Official Portal</div>
                      <div className="source-name">{checklist.university_domain} Admissions</div>
                    </div>
                    <div className="source-card source-government">
                      <div className="source-type">🇮🇳 Government Standards</div>
                      <div className="source-name">{checklist.counseling_body || "JoSAA / AICTE"}</div>
                    </div>
                    <div className="source-card source-community">
                      <div className="source-type">👥 Student Experiences</div>
                      <div className="source-name">Quora Physical Reporting Guide</div>
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className="disclaimer-callout">
              <span className="callout-icon">ℹ️</span>
              <p>{checklist.disclaimer}</p>
            </div>

            {/* Progress summary */}
            <div className="upload-summary-bar">
              <span>
                Uploaded: <b>{uploadedCount}</b> of <b>{mandatoryCount}</b> mandatory documents ({totalReqCount} total)
              </span>
              <div className="mini-progress-track">
                <div
                  className="mini-progress-fill"
                  style={{
                    width: `${Math.min(100, Math.round((uploadedCount / Math.max(1, mandatoryCount)) * 100))}%`,
                  }}
                ></div>
              </div>
            </div>

            {/* Document Upload Items */}
            <div className="requirements-list">
              {checklist.requirements.map((item, index) => {
                const isUploaded = !!files[item.id];
                const currentFile = files[item.id];

                return (
                  <div
                    key={item.id}
                    className={`req-item ${item.required ? "req-mandatory" : "req-optional"} ${isUploaded ? "req-uploaded" : ""}`}
                  >
                    <div className="req-item-left">
                      <div className="req-num">{index + 1}</div>
                      <div className="req-body">
                        <div className="req-title-row">
                          <span className="req-title">{item.title}</span>
                          {item.required ? (
                            <span className="badge-required">Mandatory</span>
                          ) : (
                            <span className="badge-optional">Optional / If Applicable</span>
                          )}
                          {item.check === "minimum_percentage" && item.value && (
                            <span className="badge-cutoff">Min {item.value}% in Class 12</span>
                          )}
                        </div>

                        <p className="req-description">{item.description}</p>

                        <div className="req-source-row">
                          <span className={`source-tag tag-${item.source_category}`}>
                            {item.source_category === "official"
                              ? "🏛️ Official Portal"
                              : item.source_category === "government"
                                ? "🇮🇳 Govt / JoSAA / AICTE"
                                : "👥 Quora / Student Guide"}
                          </span>
                          <span className="source-name-lbl">{item.source_name}</span>
                          <a
                            href={item.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="source-verify-link"
                          >
                            Source Link ↗
                          </a>
                        </div>
                      </div>
                    </div>

                    <div className="req-item-right">
                      {isUploaded ? (
                        <div className="file-uploaded-chip">
                          <span className="file-icon">📄</span>
                          <div className="file-info">
                            <span className="file-name" title={currentFile.name}>
                              {currentFile.name}
                            </span>
                            <span className="file-size">
                              {(currentFile.size / 1024).toFixed(1)} KB
                            </span>
                          </div>
                          <button
                            type="button"
                            className="btn-remove-file"
                            onClick={() => handleFileChange(item.id, null)}
                            title="Remove file"
                          >
                            ✕
                          </button>
                        </div>
                      ) : (
                        <label className="file-upload-dropzone">
                          <input
                            type="file"
                            accept=".pdf,.png,.jpg,.jpeg,.txt"
                            onChange={(e) => {
                              const f = e.target.files?.[0];
                              if (f) handleFileChange(item.id, f);
                            }}
                          />
                          <span className="upload-icon">📁</span>
                          <span className="upload-text">Upload Document</span>
                          <span className="upload-hint">PDF, JPG, PNG up to 10MB</span>
                        </label>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="verification-action-panel">
              <button
                type="button"
                className="btn btn-success btn-verify"
                disabled={loading || !applicantName.trim()}
                onClick={submitVerification}
              >
                {loading ? (
                  <>
                    <span className="spinner"></span>
                    <span>AI Agents Verifying Documents…</span>
                  </>
                ) : (
                  <>
                    <span>Run Agentic Document Verification</span>
                  </>
                )}
              </button>
              {uploadedCount < mandatoryCount && (
                <span className="action-hint">
                  ⚠️ Note: {mandatoryCount - uploadedCount} mandatory document(s) remaining.
                </span>
              )}
            </div>
          </section>
        )}

        {/* Step 3: Verification Dashboard */}
        {result && (
          <section className="glass-card results-card" id="verification-results">
            <div className="section-header">
              <div className="step-indicator success">✓</div>
              <div>
                <h2>Admission Document Verification Report</h2>
                <p className="text-muted">
                  Evaluated for <b>{result.applicant_name}</b> · {result.university_name}
                </p>
              </div>
            </div>

            <div className="dashboard-grid">
              {/* Readiness Score Card */}
              <div className="score-widget">
                <div
                  className={`score-circle ${result.readiness_score >= 80
                      ? "score-high"
                      : result.readiness_score >= 50
                        ? "score-mid"
                        : "score-low"
                    }`}
                >
                  <span className="score-number">{result.readiness_score}%</span>
                  <span className="score-label">Admission Readiness</span>
                </div>
                <div className="score-summary">
                  <h4>
                    {result.readiness_score === 100
                      ? "🎉 100% Ready for Physical Reporting"
                      : result.readiness_score >= 70
                        ? "⚡ Good Readiness (Minor Actions Needed)"
                        : "⚠️ Incomplete (Action Required)"}
                  </h4>
                  <p>
                    {result.readiness_score === 100
                      ? "All required documents meet the admission criteria of the institution and regulatory authorities."
                      : "Review the missing documents or validation warnings below prior to campus reporting."}
                  </p>
                  <a
                    className="btn btn-download-pdf"
                    href={result.report_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    📥 Download Official PDF Verification Certificate
                  </a>
                </div>
              </div>

              {/* Validation Breakdown */}
              <div className="validation-results-panel">
                <h3>Verification Rule Breakdown</h3>
                <div className="results-list">
                  {result.results.map((res, index) => (
                    <div key={index} className={`result-card status-${res.status}`}>
                      <div className="result-status-icon">
                        {res.status === "passed"
                          ? "✅"
                          : res.status === "warning"
                            ? "⚠️"
                            : "❌"}
                      </div>
                      <div className="result-content">
                        <div className="result-title-row">
                          <span className="result-title">{res.title}</span>
                          <span className={`status-pill pill-${res.status}`}>
                            {res.status.toUpperCase()}
                          </span>
                        </div>
                        <p className="result-message">{res.message}</p>
                        {res.evidence && (
                          <div className="result-evidence">
                            <span>Verified File:</span> <code>{res.evidence}</code>
                          </div>
                        )}
                        {res.source_url && (
                          <a
                            href={res.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="result-source-link"
                          >
                            Source: {res.source_name || "Official Norm"} ↗
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Suggested Next Steps for Physical Reporting */}
              {result.suggestions.length > 0 && (
                <div className="suggestions-panel">
                  <h3>📋 Recommended Next Steps for Campus Physical Reporting</h3>
                  <ul className="suggestions-list">
                    {result.suggestions.map((sug, idx) => (
                      <li key={idx} className="suggestion-item">
                        <span className="sug-bullet">👉</span>
                        <span>{sug}</span>
                      </li>
                    ))}
                    <li className="suggestion-item">
                      <span className="sug-bullet">👉</span>
                      <span>
                        Carry at least 3 sets of self-attested photocopies of all verified documents along with 6-8 recent passport-size photographs.
                      </span>
                    </li>
                  </ul>
                </div>
              )}

              {/* Traceable Agent Audit Trail */}
              <details className="audit-accordion">
                <summary>
                  <span>🤖 Traceable Multi-Agent Activity & OCR Logs ({result.audit_trail.length} steps)</span>
                </summary>
                <ol className="audit-list">
                  {result.audit_trail.map((step, idx) => (
                    <li key={idx} className="audit-item">
                      <span className="audit-step-badge">Step {idx + 1}</span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ol>
              </details>
            </div>
          </section>
        )}
      </main>

      <footer className="site-footer">
        <p>
          Indian Engineering Colleges Verification Assistant · Powered by Agentic Multi-Source Intelligence · JoSAA, AICTE, State CETs & Student Community Knowledge
        </p>
      </footer>
    </div>
  );
}
