import { apiFetch } from "./client";


function wait(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}


export async function analyzeClaim(claim, waitForAll, onProgress) {
  let job = await apiFetch("/api/claims/analysis-jobs", {
    method: "POST",
    body: JSON.stringify({
      claim,
      wait_for_all: waitForAll,
    }),
  });

  onProgress(job);

  while (job.status === "queued" || job.status === "running") {
    await wait(600);
    job = await apiFetch(`/api/claims/analysis-jobs/${job.job_id}`);
    onProgress(job);
  }

  if (job.status === "failed") {
    throw new Error(job.error || "The AI models could not complete this analysis.");
  }

  if (!job.result) {
    throw new Error("The analysis completed without a result.");
  }

  return job.result;
}
