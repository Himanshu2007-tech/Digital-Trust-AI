"use client";

import React, { useState, useRef, useCallback } from "react";
import { Upload, X, File, AlertCircle, CheckCircle2, Film, Music, Image as ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

export interface FileDropzoneProps {
  accept: string;
  mediaType: "image" | "audio" | "video" | "any";
  maxSizeMB?: number;
  onFileSelect?: (file: File | null) => void;
  className?: string;
}

export function FileDropzone({
  accept,
  mediaType,
  maxSizeMB = 50,
  onFileSelect,
  className,
}: FileDropzoneProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [duration, setDuration] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateAndSetFile = useCallback(
    (file: File) => {
      setError(null);
      // Validate file size
      const maxSizeBytes = maxSizeMB * 1024 * 1024;
      if (file.size > maxSizeBytes) {
        setError(`File size (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds the maximum limit of ${maxSizeMB} MB.`);
        return;
      }

      // Validate media type
      if (mediaType === "image" && !file.type.startsWith("image/")) {
        setError(`Invalid file type "${file.type}". Please upload an image file (JPG, PNG, WebP, GIF).`);
        return;
      }
      if (mediaType === "audio" && !file.type.startsWith("audio/")) {
        setError(`Invalid file type "${file.type}". Please upload an audio file (MP3, WAV, OGG, M4A).`);
        return;
      }
      if (mediaType === "video" && !file.type.startsWith("video/")) {
        setError(`Invalid file type "${file.type}". Please upload a video file (MP4, WebM, QuickTime).`);
        return;
      }

      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);

      // Extract duration if video
      if (mediaType === "video") {
        const tempVideo = document.createElement("video");
        tempVideo.preload = "metadata";
        tempVideo.src = url;
        tempVideo.onloadedmetadata = () => {
          const mins = Math.floor(tempVideo.duration / 60);
          const secs = Math.floor(tempVideo.duration % 60);
          setDuration(`${mins}:${secs < 10 ? "0" : ""}${secs}`);
        };
      } else {
        setDuration(null);
      }

      if (onFileSelect) onFileSelect(file);
    },
    [maxSizeMB, mediaType, onFileSelect]
  );

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleRemove = () => {
    setSelectedFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    setDuration(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (onFileSelect) onFileSelect(null);
  };

  const MediaIcon =
    mediaType === "image" ? ImageIcon : mediaType === "audio" ? Music : Film;

  return (
    <div className={cn("space-y-3", className)}>
      {!selectedFile ? (
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
          tabIndex={0}
          role="button"
          aria-label={`Upload ${mediaType} file`}
          className={cn(
            "relative flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-2xl cursor-pointer transition-all focus:outline-none focus:ring-2 focus:ring-cyan-500/50",
            dragActive
              ? "border-cyan-500 bg-cyan-500/10 scale-[1.01]"
              : "border-slate-300 dark:border-surface-borderDark hover:border-cyan-500/60 dark:hover:border-cyan-500/50 bg-slate-50/50 dark:bg-surface-cardDark/40 hover:bg-slate-100/50 dark:hover:bg-surface-cardDark/80"
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={accept}
            onChange={handleChange}
            className="hidden"
          />
          <div className="p-3.5 mb-3 rounded-2xl bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20">
            <MediaIcon className="w-8 h-8" />
          </div>
          <p className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-1 text-center">
            Click to browse or drag & drop {mediaType} file here
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 text-center max-w-sm">
            Supported formats: <strong className="font-mono text-slate-700 dark:text-slate-300">{accept}</strong> (Max size: {maxSizeMB} MB)
          </p>
        </div>
      ) : (
        /* Selected File Preview Card */
        <div className="rounded-2xl border border-slate-200 dark:border-surface-borderDark bg-white dark:bg-surface-cardDark p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-surface-borderDark">
            <div className="flex items-center gap-3 min-w-0">
              <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 shrink-0">
                <MediaIcon className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
                  {selectedFile.name}
                </p>
                <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 font-mono">
                  <span>{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</span>
                  <span>•</span>
                  <span className="uppercase">{selectedFile.type || "Unknown"}</span>
                  {duration && (
                    <>
                      <span>•</span>
                      <span>Duration: {duration}</span>
                    </>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={handleRemove}
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
              title="Remove file"
              aria-label="Remove file"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Media Preview Area */}
          {previewUrl && (
            <div className="rounded-xl overflow-hidden bg-slate-950/5 dark:bg-slate-950/40 p-2 border border-slate-200/60 dark:border-surface-borderDark flex items-center justify-center">
              {mediaType === "image" && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={previewUrl}
                  alt={selectedFile.name}
                  className="max-h-72 w-auto object-contain rounded-lg shadow-sm"
                />
              )}
              {mediaType === "audio" && (
                <div className="w-full py-4 px-2">
                  <audio controls className="w-full" src={previewUrl}>
                    Your browser does not support the audio element.
                  </audio>
                </div>
              )}
              {mediaType === "video" && (
                <video
                  controls
                  className="max-h-80 w-full object-contain rounded-lg shadow-sm"
                  src={previewUrl}
                >
                  Your browser does not support the video element.
                </video>
              )}
            </div>
          )}
        </div>
      )}

      {/* Error Message Callout */}
      {error && (
        <div className="rounded-xl border border-rose-200 dark:border-rose-500/30 bg-rose-50 dark:bg-rose-950/20 p-3 text-xs text-rose-800 dark:text-rose-200 flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
