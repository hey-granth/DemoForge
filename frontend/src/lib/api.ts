const API_BASE = "/api";

export interface JobResponse {
    job_id: string;
    status: string;
    created_at: string;
}

export interface JobStatus {
    job_id: string;
    status: "pending" | "processing" | "completed" | "failed";
    created_at: string;
    updated_at: string;
    error: string | null;
}

export async function submitJob(url: string): Promise<JobResponse> {
    const response = await fetch(`${API_BASE}/demo/run`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Failed to submit job" }));
        throw new Error(error.detail || "Failed to submit job");
    }

    return response.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
    const response = await fetch(`${API_BASE}/demo/status/${jobId}`);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Failed to get status" }));
        throw new Error(error.detail || "Failed to get status");
    }

    return response.json();
}

export async function downloadVideo(jobId: string): Promise<void> {
    const response = await fetch(`${API_BASE}/demo/export/${jobId}`);

    if (!response.ok) {
        throw new Error("Failed to download video");
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `demo-${jobId}.mp4`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
