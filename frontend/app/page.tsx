"use client";

import { useEffect } from "react";

export default function Page() {
  useEffect(() => {
    const fid = localStorage.getItem("farmerId");
    window.location.href = fid ? "/home" : "/onboarding";
  }, []);
  
  return <div style={{background:"#0d1f15",minHeight:"100dvh"}}/>;
}
