"use client";

import { useEffect, useState } from "react";
import { JobState } from "@/hooks/useJobPolling";

interface ProgressProps {
    state: JobState;
    onReset: () => void;
}

function getStatusMessage(state: JobState): string {
    switch (state.status) {
        case "submitting":
            return "Connecting";
        case "polling":
            switch (state.jobStatus) {
                case "pending":
                    return "Opening";
                case "processing":
                    return "Recording";
                default:
                    return "Processing";
            }
        case "downloading":
            return "Exporting";
        case "complete":
            return "Complete";
        default:
            return "";
    }
}

function getProgressPercent(state: JobState): number {
    switch (state.status) {
        case "submitting":
            return 15;
        case "polling":
            switch (state.jobStatus) {
                case "pending":
                    return 35;
                case "processing":
                    return 70;
                default:
                    return 50;
            }
        case "downloading":
            return 90;
        case "complete":
            return 100;
        default:
            return 0;
    }
}

export function Progress({ state, onReset }: ProgressProps) {
    const [elapsed, setElapsed] = useState(0);

    useEffect(() => {
        if (state.status === "idle" || state.status === "complete" || state.status === "error") {
            return;
        }

        setElapsed(0);
        const interval = setInterval(() => {
            setElapsed((prev) => prev + 1);
        }, 1000);

        return () => clearInterval(interval);
    }, [state.status]);

    if (state.status === "idle") return null;

    // Error state
    if (state.status === "error") {
        return (
            <div className="executionContainer">
                <div className="executionCard errorCard">
                    <div className="errorContent">
                        <div className="errorIcon">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <line x1="18" y1="6" x2="6" y2="18" />
                                <line x1="6" y1="6" x2="18" y2="18" />
                            </svg>
                        </div>
                        <h3 className="errorTitle">Generation failed</h3>
                        <p className="errorMessage">{state.message}</p>
                        <button className="retryButton" onClick={onReset}>
                            Try again
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // Complete state
    if (state.status === "complete") {
        return (
            <div className="executionContainer">
                <div className="executionCard completeCard">
                    <div className="completeContent">
                        <div className="completeIcon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                <polyline points="20 6 9 17 4 12" />
                            </svg>
                        </div>
                        <h3 className="completeTitle">Demo ready</h3>
                        <p className="completeSubtitle">Download started</p>
                        <button className="resetButton" onClick={onReset}>
                            Generate another
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // Processing states
    const statusMessage = getStatusMessage(state);
    const progressPercent = getProgressPercent(state);
    const url = "url" in state ? state.url : "";

    return (
        <div className="executionContainer">
            <div className="executionCard">
                <div className="executionHeader">
                    <div className="executionStatus">
                        <div className="statusIndicator active" />
                        <span className="statusText">{statusMessage}</span>
                    </div>
                </div>
                <div className="executionProgress">
                    <div
                        className="progressLine"
                        style={{ width: `${progressPercent}%` }}
                    />
                </div>
                <div className="executionBody">
                    <p className="executionUrl">{url}</p>
                </div>
            </div>
        </div>
    );
}
