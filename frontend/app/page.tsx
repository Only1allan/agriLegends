"use client";

import { useEffect } from "react";

export default function Page() {
  useEffect(() => {
    const token = localStorage.getItem("farmwise_token");
    window.location.href = token ? "/dashboard" : "/login";
  }, []);

  return <div className="bg-soil-900 min-h-dvh" />;
}
