const TRACE_GROUPS = [
  ["Supporting evidence", "supporting_evidence"],
  ["Contradicting evidence", "contradicting_evidence"],
  ["Missing context", "missing_context"],
];


function ReasoningTrace({ result }) {
  return (
    <div className="reasoning-trace">
      <h4>Reasoning Trace</h4>

      <div className="reasoning-trace-grid">
        {TRACE_GROUPS.map(([label, field]) => {
          const items = result[field] || [];

          return (
            <section key={field}>
              <h5>{label}</h5>
              {items.length > 0 ? (
                <ul>
                  {items.map((item, index) => (
                    <li key={`${field}-${index}`}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p>None provided by this model.</p>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}


export default ReasoningTrace;
