"use client";

import { Hero } from "@/components/Hero";
import { Progress } from "@/components/Progress";
import { Footer } from "@/components/Footer";
import { useJobPolling } from "@/hooks/useJobPolling";

export default function Home() {
  const { state, submit, reset } = useJobPolling();

  const isProcessing =
    state.status === "submitting" ||
    state.status === "polling" ||
    state.status === "downloading";

  return (
    <>
      <main className="main">
        <Hero onSubmit={submit} isDisabled={isProcessing} />
        <Progress state={state} onReset={reset} />
      </main>
      <Footer />
    </>
  );
}
