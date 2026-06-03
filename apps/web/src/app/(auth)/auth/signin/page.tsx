"use client";

import { signIn } from "next-auth/react";
import { Clock } from "lucide-react";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-850">
      <div className="bg-white p-9 rounded-xl shadow-[0_4px_24px_rgba(0,0,0,0.28)] w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-11 h-11 bg-primary-500 rounded-xl mx-auto mb-4 flex items-center justify-center">
            <Clock size={20} strokeWidth={2} className="text-white" />
          </div>
          <h1 className="text-xl font-semibold text-neutral-900">MeetingMind</h1>
          <p className="text-sm text-neutral-400 mt-1.5">Every commitment, tracked.</p>
        </div>

        <button
          onClick={() => signIn("google", { callbackUrl: "/meetings" })}
          className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-neutral-200 rounded text-sm font-medium text-neutral-700 hover:bg-neutral-50 shadow-sm transition-colors duration-fast"
        >
          <GoogleIcon />
          Continue with Google
        </button>

        <p className="text-[11px] text-neutral-300 text-center mt-4">
          By continuing you agree to our Terms of Service.
        </p>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 18 18" fill="none">
      <path d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
      <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
    </svg>
  );
}
