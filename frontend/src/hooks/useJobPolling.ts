"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { submitJob, getJobStatus, downloadVideo, JobStatus } from "@/lib/api";

export type JobState =
    | { status: "idle" }
    | { status: "submitting"; url: string }
    | { status: "polling"; jobId: string; url: string; jobStatus: JobStatus["status"] }
    | { status: "downloading"; jobId: string; url: string }
    | { status: "complete"; jobId: string; url: string }
    | { status: "error"; message: string; url?: string };

const POLL_INTERVAL = 2000;
const MAX_POLL_DURATION = 360000; // 6 minutes

export function useJobPolling() {
    const [state, setState] = useState<JobState>({ status: "idle" });
    const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const pollStartRef = useRef<number>(0);

    const clearPolling = useCallback(() => {
        if (pollTimeoutRef.current) {
            clearTimeout(pollTimeoutRef.current);
            pollTimeoutRef.current = null;
        }
    }, []);

    const reset = useCallback(() => {
        clearPolling();
        setState({ status: "idle" });
    }, [clearPolling]);

    const submit = useCallback(async (url: string) => {
        clearPolling();
        setState({ status: "submitting", url });

        try {
            const job = await submitJob(url);
            pollStartRef.current = Date.now();
            setState({
                status: "polling",
                jobId: job.job_id,
                url,
                jobStatus: "pending",
            });
        } catch (err) {
            setState({
                status: "error",
                message: err instanceof Error ? err.message : "Failed to submit",
                url,
            });
        }
    }, [clearPolling]);

    // Polling effect
    useEffect(() => {
        if (state.status !== "polling") return;

        const poll = async () => {
            try {
                // Check timeout
                if (Date.now() - pollStartRef.current > MAX_POLL_DURATION) {
                    setState({
                        status: "error",
                        message: "Demo generation timed out. Please try again.",
                        url: state.url,
                    });
                    return;
                }

                const status = await getJobStatus(state.jobId);

                if (status.status === "completed") {
                    setState({
                        status: "downloading",
                        jobId: state.jobId,
                        url: state.url,
                    });
                } else if (status.status === "failed") {
                    setState({
                        status: "error",
                        message: status.error || "Demo generation failed",
                        url: state.url,
                    });
                } else {
                    // Update polling state with current job status
                    setState((prev) => {
                        if (prev.status === "polling") {
                            return { ...prev, jobStatus: status.status };
                        }
                        return prev;
                    });
                    // Schedule next poll
                    pollTimeoutRef.current = setTimeout(poll, POLL_INTERVAL);
                }
            } catch (err) {
                setState({
                    status: "error",
                    message: err instanceof Error ? err.message : "Connection error",
                    url: state.url,
                });
            }
        };

        poll();

        return () => clearPolling();
    }, [state.status, state.status === "polling" ? state.jobId : null, clearPolling]);

    // Download effect
    useEffect(() => {
        if (state.status !== "downloading") return;

        const doDownload = async () => {
            try {
                await downloadVideo(state.jobId);
                setState({
                    status: "complete",
                    jobId: state.jobId,
                    url: state.url,
                });
            } catch (err) {
                setState({
                    status: "error",
                    message: "Failed to download video",
                    url: state.url,
                });
            }
        };

        doDownload();
    }, [state.status, state.status === "downloading" ? state.jobId : null]);

    return { state, submit, reset };
}
