"use client";

import { Trash2 } from "lucide-react";
import { Note } from "@/app/page";

interface NoteListProps {
  notes: Note[];
  selectedNoteId: string | null;
  onSelectNote: (id: string) => void;
  onDeleteNote: (id: string) => void;
}

export default function NoteList({
  notes,
  selectedNoteId,
  onSelectNote,
  onDeleteNote,
}: NoteListProps) {
  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffTime = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return date.toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit",
      });
    } else if (diffDays === 1) {
      return "Yesterday";
    } else if (diffDays < 7) {
      return date.toLocaleDateString("en-US", { weekday: "short" });
    } else {
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
    }
  };

  const getPreview = (content: string) => {
    const text = content.replace(/\n/g, " ").trim();
    return text.length > 60 ? text.substring(0, 60) + "..." : text;
  };

  return (
    <div className="divide-y divide-gray-200 dark:divide-gray-800">
      {notes.map((note) => (
        <div
          key={note.id}
          onClick={() => onSelectNote(note.id)}
          className={`p-4 cursor-pointer transition-colors group hover:bg-gray-50 dark:hover:bg-gray-800 ${
            selectedNoteId === note.id
              ? "bg-blue-50 dark:bg-blue-950/30 border-l-4 border-l-blue-500"
              : ""
          }`}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <h3
                className={`font-semibold text-sm mb-1 truncate ${
                  selectedNoteId === note.id
                    ? "text-blue-700 dark:text-blue-300"
                    : "text-gray-900 dark:text-white"
                }`}
              >
                {note.title || "Untitled Note"}
              </h3>
              {note.content && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 line-clamp-2">
                  {getPreview(note.content)}
                </p>
              )}
              <p className="text-xs text-gray-400 dark:text-gray-500">
                {formatDate(note.updatedAt)}
              </p>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDeleteNote(note.id);
              }}
              className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-all"
              aria-label="Delete note"
            >
              <Trash2 className="w-4 h-4 text-red-500" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
