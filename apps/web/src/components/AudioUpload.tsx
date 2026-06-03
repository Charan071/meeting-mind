"use client";

import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Upload } from "lucide-react";

interface Props {
  meetingId: string;
}

export function AudioUpload({ meetingId }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const queryClient = useQueryClient();

  const { mutate, isPending, isError, error } = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/meetings/${meetingId}/upload-audio`,
        { method: "POST", body: form }
      );
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["meeting", meetingId] });
    },
  });

  const handleFile = (file: File) => {
    if (file.size > 25 * 1024 * 1024) {
      alert("File too large — max 25 MB");
      return;
    }
    mutate(file);
  };

  return (
    <div
      className={`border-2 border-dashed rounded p-6 text-center cursor-pointer transition-colors duration-fast ${
        dragOver ? "border-primary-500 bg-primary-50" : "border-neutral-200 hover:border-neutral-300"
      }`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".mp3,.mp4,.m4a,.wav,.webm,.ogg"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />

      <Upload className="mx-auto mb-2 text-neutral-400" size={24} />

      {isPending ? (
        <p className="text-sm text-neutral-500">Uploading & transcribing…</p>
      ) : (
        <>
          <p className="text-sm font-medium text-neutral-700">Upload audio recording</p>
          <p className="text-xs text-neutral-400 mt-1">MP3, MP4, M4A, WAV, WebM · max 25 MB</p>
        </>
      )}

      {isError && (
        <p className="text-xs text-red-600 mt-2">
          {(error as Error).message}
        </p>
      )}
    </div>
  );
}
