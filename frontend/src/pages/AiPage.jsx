import React from "react";
import "./AiPage.css";

const stats = [
  { value: "92%", label: "Order prediction accuracy" },
  { value: "38%", label: "Faster dispatch decisions" },
  { value: "24/7", label: "Live optimization engine" },
  { value: "4.8/5", label: "Operator confidence score" },
];

const featureCards = [
  { title: "Demand Forecasting", text: "Predict peak windows, menu demand, rider saturation, and zone-level pressure before it hurts delivery time.", icon: "chart" },
  { title: "Smart Dispatch", text: "Prioritize riders by proximity, availability, order density, and delivery urgency with transparent assignment logic.", icon: "spark" },
  { title: "Menu Intelligence", text: "Highlight best-performing dishes, identify slow sellers, and surface bundling opportunities that lift cart value.", icon: "menu" },
  { title: "Ops Co-Pilot", text: "Give admins a real-time AI console for recommendations, alerts, anomalies, and action summaries across the fleet.", icon: "shield" },
  { title: "Customer Insights", text: "Understand repeat patterns, churn risk, cuisine affinity, and price sensitivity without digging through raw tables.", icon: "user" },
  { title: "Auto Alerts", text: "Detect late orders, overloaded zones, unavailable riders, and restaurant bottlenecks before they become complaints.", icon: "pulse" },
];

const trustItems = [
  "Secure operational workflows",
  "Human-readable recommendations",
  "Fast decisions during peak load",
  "Built for real delivery teams",
];

// Reusable Icon Component (Internal to this page)
function Icon({ type }) {
  const common = { width: 22, height: 22, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": "true" };
  switch (type) {
    case "chart": return <svg {...common}><path d="M4 19V5M4 19h16M8 15l3-3 3 2 5-6" /><circle cx="8" cy="15" r="1" /><circle cx="11" cy="12" r="1" /><circle cx="14" cy="14" r="1" /><circle cx="19" cy="8" r="1" /></svg>;
    case "spark": return <svg {...common}><path d="M12 3l1.7 4.8L19 9.5l-4.2 3 1.5 5-4.3-3.1L7.7 17.5l1.5-5L5 9.5l5.3-1.7L12 3z" /></svg>;
    case "menu": return <svg {...common}><path d="M5 6h14M5 12h14M5 18h9" /><circle cx="17.5" cy="18" r="1.5" /></svg>;
    case "shield": return <svg {...common}><path d="M12 3l7 3v5c0 4.2-2.7 8-7 10-4.3-2-7-5.8-7-10V6l7-3zM9.5 12l1.8 1.8L15 10" /></svg>;
    case "user": return <svg {...common}><circle cx="12" cy="8" r="3.2" /><path d="M5 19c1.8-3 4.2-4.5 7-4.5s5.2 1.5 7 4.5" /></svg>;
    case "pulse": return <svg {...common}><path d="M3 12h4l2-4 4 8 2-4h6" /></svg>;
    case "arrow": return <svg {...common}><path d="M5 12h14M13 6l6 6-6 6" /></svg>;
    default: return <svg {...common}><circle cx="12" cy="12" r="8" /></svg>;
  }
}

export default function AiPage() {
  return (
    <main className="ai-page">
      <section className="ai-hero">
        <div className="ai-shell">
          <div className="ai-hero-grid">
            <div className="ai-hero-copy">
              <span className="ai-badge">FusionDrop Intelligence Suite</span>
              <h1>AI that makes delivery <span> faster, greener, sharper.</span></h1>
              <p className="ai-lead">Turn operational noise into decisions. Forecast demand, optimize dispatch, and give your team a serious control layer.</p>
              <div className="ai-hero-actions">
                <button className="ai-btn ai-btn-primary">Explore AI Dashboard <Icon type="arrow" /></button>
                <button className="ai-btn ai-btn-secondary">View Capabilities</button>
              </div>
              <ul className="ai-trust-list">
                {trustItems.map(i => <li key={i}>{i}</li>)}
              </ul>
            </div>

            <div className="ai-hero-panel">
              <div className="ai-panel-top">
                <div className="ai-panel-chip">Live orchestration</div>
                <div className="ai-panel-dot-group"><span /><span /><span /></div>
              </div>
              <div className="ai-command-box">
                <div className="ai-command-label">AI recommendation</div>
                <p>Reassign 12 Koramangala orders to Zone B riders to prevent SLA breach.</p>
              </div>
              <div className="ai-panel-grid">
                <div className="ai-mini-card"><span>Demand spike</span><strong>+18%</strong><small>HSR Layout</small></div>
                <div className="ai-mini-card"><span>Dispatch load</span><strong>71%</strong><small>Optimal</small></div>
              </div>
            </div>
          </div>

          <div className="ai-metrics-grid">
            {stats.map(s => (
              <article key={s.label} className="ai-metric-card">
                <div className="ai-metric-value">{s.value}</div>
                <p className="ai-metric-label">{s.label}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* Feature Section */}
      <section className="ai-section">
        <div className="ai-shell">
          <div className="ai-section-head">
            <span className="ai-kicker">Capability stack</span>
            <h2>Serious Intelligence Layer</h2>
          </div>
          <div className="ai-features-grid">
            {featureCards.map(f => (
              <article key={f.title} className="ai-feature-card">
                <div className="ai-feature-icon"><Icon type={f.icon} /></div>
                <h3>{f.title}</h3>
                <p>{f.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom Proof Section */}
      <section className="ai-section ai-section-alt">
        <div className="ai-shell">
          <div className="ai-split-grid">
            <div className="ai-story-card">
              <h2>Rich UI + Business Outcomes</h2>
              <p>Visual density signals reliability to stakeholders.</p>
            </div>
            <div className="ai-proof-card">
              <div className="ai-proof-top">
                <h3>Operator Snapshot</h3>
                <span className="ai-proof-pill">Peak Hour</span>
              </div>
              <div className="ai-proof-grid">
                <div className="ai-proof-metric"><strong>1.2s</strong><span>Avg Response</span></div>
                <div className="ai-proof-metric"><strong>94%</strong><span>SLA Adherence</span></div>
              </div>
              <p className="ai-proof-summary">Current system health is optimal. No bottlenecks detected.</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}