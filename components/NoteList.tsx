"use client";

import { Trash2, Pin, PinOff } from "lucide-react";
import { Note } from "@/app/page";

interface NoteListProps {
  notes: Note[];
  selectedNoteId: string | null;
  onSelectNote: (id: string) => void;
  onDeleteNote: (id: string) => void;
  onTogglePin: (id: string) => void;
  searchQuery: string;
}

export default function NoteList({
  notes,
  selectedNoteId,
  onSelectNote,
  onDeleteNote,
  onTogglePin,
  searchQuery,
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

  const highlightText = (text: string, query: string) => {
    if (!query) return text;
    const parts = text.split(new RegExp(`(${query})`, "gi"));
    return parts.map((part, i) =>
      part.toLowerCase() === query.toLowerCase() ? (
        <mark key={i} className="bg-yellow-200 dark:bg-yellow-900/50 px-0.5 rounded">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className="divide-y divide-gray-200 dark:divide-gray-800">
      {notes.map((note) => (
        <div
          key={note.id}
          onClick={() => onSelectNote(note.id)}
          className={`p-4 cursor-pointer transition-all duration-150 group hover:bg-gray-50 dark:hover:bg-gray-800 ${
            selectedNoteId === note.id
              ? "bg-blue-50 dark:bg-blue-950/30 border-l-4 border-l-blue-500"
              : ""
          } ${note.pinned ? "bg-amber-50/50 dark:bg-amber-950/10" : ""}`}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                {note.pinned && (
                  <Pin className="w-3 h-3 text-amber-500 shrink-0" fill="currentColor" />
                )}
                <h3
                  className={`font-semibold text-sm truncate ${
                    selectedNoteId === note.id
                      ? "text-blue-700 dark:text-blue-300"
                      : "text-gray-900 dark:text-white"
                  }`}
                >
                  {searchQuery ? highlightText(note.title || "Untitled Note", searchQuery) : (note.title || "Untitled Note")}
                </h3>
              </div>
              {note.content && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 line-clamp-2">
                  {searchQuery ? highlightText(getPreview(note.content), searchQuery) : getPreview(note.content)}
                </p>
              )}
              <p className="text-xs text-gray-400 dark:text-gray-500">
                {formatDate(note.updatedAt)}
              </p>
            </div>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onTogglePin(note.id);
                }}
                className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                aria-label={note.pinned ? "Unpin note" : "Pin note"}
                title={note.pinned ? "Unpin" : "Pin"}
              >
                {note.pinned ? (
                  <Pin className="w-4 h-4 text-amber-500" fill="currentColor" />
                ) : (
                  <PinOff className="w-4 h-4 text-gray-400" />
                )}
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteNote(note.id);
                }}
                className="p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                aria-label="Delete note"
              >
                <Trash2 className="w-4 h-4 text-red-500" />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
