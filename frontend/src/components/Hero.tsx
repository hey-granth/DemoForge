"use client";

import { useState, FormEvent } from "react";

interface HeroProps {
    onSubmit: (url: string) => void;
    isDisabled: boolean;
}

export function Hero({ onSubmit, isDisabled }: HeroProps) {
    const [url, setUrl] = useState("");

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        if (url.trim() && !isDisabled) {
            let normalizedUrl = url.trim();
            if (!normalizedUrl.startsWith("http://") && !normalizedUrl.startsWith("https://")) {
                normalizedUrl = "https://" + normalizedUrl;
            }
            onSubmit(normalizedUrl);
        }
    };

    return (
        <section className="hero">
            <div className="heroContent">
                <h1 className="headline">
                    Paste a URL.<br />
                    Get a demo.
                </h1>
                <p className="subline">
                    Product videos from any website, instantly.
                </p>
            </div>

            <div className="glassContainer">
                <form className="inputModule" onSubmit={handleSubmit}>
                    <div className={`inputWrapper ${isDisabled ? "disabled" : ""}`}>
                        <input
                            type="text"
                            className="urlInput"
                            placeholder="yourproduct.com"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            disabled={isDisabled}
                            autoFocus
                            spellCheck={false}
                            autoComplete="off"
                        />
                        <button
                            type="submit"
                            className="submitButton"
                            disabled={isDisabled || !url.trim()}
                        >
                            Generate
                        </button>
                    </div>
                </form>
            </div>

            {/* Feature Icons Row */}
            <div className="featureRow">
                <div className="featureItem">
                    <svg className="featureIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <polyline points="12,6 12,12 16,14" />
                    </svg>
                    <span className="featureLabel">60-second videos</span>
                </div>
                <div className="featureItem">
                    <svg className="featureIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 2L2 7l10 5 10-5-10-5z" />
                        <path d="M2 17l10 5 10-5" />
                        <path d="M2 12l10 5 10-5" />
                    </svg>
                    <span className="featureLabel">AI-powered</span>
                </div>
                <div className="featureItem">
                    <svg className="featureIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                        <polyline points="7,10 12,15 17,10" />
                        <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                    <span className="featureLabel">Instant download</span>
                </div>
            </div>

            {/* Social Proof */}
            <div className="socialProof">
                <p className="socialProofText">"The fastest way to create product demos" — Early users</p>
            </div>
        </section>
    );
}
