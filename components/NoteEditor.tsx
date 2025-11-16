"use client";

import { useState, useEffect, useRef } from "react";
import { Trash2, Save } from "lucide-react";
import { Note } from "@/app/page";

interface NoteEditorProps {
  note: Note;
  onUpdateNote: (id: string, updates: Partial<Note>) => void;
  onDeleteNote: (id: string) => void;
}

export default function NoteEditor({
  note,
  onUpdateNote,
  onDeleteNote,
}: NoteEditorProps) {
  const [title, setTitle] = useState(note.title);
  const [content, setContent] = useState(note.content);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const titleRef = useRef<HTMLInputElement>(null);
  const contentRef = useRef<HTMLTextAreaElement>(null);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    setTitle(note.title);
    setContent(note.content);
    setLastSaved(new Date(note.updatedAt));
  }, [note.id, note.title, note.content, note.updatedAt]);

  // Auto-save with debounce
  useEffect(() => {
    // Skip auto-save if content hasn't changed from the original note
    if (title === note.title && content === note.content) {
      return;
    }

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    setIsSaving(true);
    saveTimeoutRef.current = setTimeout(() => {
      onUpdateNote(note.id, { title, content });
      setIsSaving(false);
      setLastSaved(new Date());
    }, 500);

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title, content, note.id]);

  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTitle = e.target.value;
    setTitle(newTitle);
    onUpdateNote(note.id, { title: newTitle });
  };

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    setContent(newContent);
    onUpdateNote(note.id, { content: newContent });
  };

  const handleDelete = () => {
    if (confirm("Are you sure you want to delete this note?")) {
      onDeleteNote(note.id);
    }
  };

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  const getWordCount = (text: string) => {
    const words = text.trim().split(/\s+/).filter((word) => word.length > 0);
    return words.length;
  };

  const getCharCount = (text: string) => {
    return text.length;
  };

  return (
    <div className="flex-1 flex flex-col bg-white dark:bg-gray-900">
      {/* Toolbar */}
      <div className="border-b border-gray-200 dark:border-gray-800 px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            {isSaving ? (
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
                <span>Saving...</span>
              </div>
            ) : lastSaved ? (
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <Save className="w-4 h-4 text-green-500" />
                <span>Saved {lastSaved.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}</span>
              </div>
            ) : null}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {getWordCount(content)} words • {getCharCount(content)} characters
          </div>
        </div>
        <button
          onClick={handleDelete}
          className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors active:scale-95"
          aria-label="Delete note"
          title="Delete note"
        >
          <Trash2 className="w-5 h-5 text-red-500" />
        </button>
      </div>

      {/* Editor */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 sm:py-8">
        <div className="max-w-4xl mx-auto">
          <input
            ref={titleRef}
            type="text"
            value={title}
            onChange={handleTitleChange}
            placeholder="Untitled Note"
            className="w-full text-3xl sm:text-4xl font-bold mb-6 bg-transparent border-none outline-none text-gray-900 dark:text-white placeholder-gray-400 resize-none focus:ring-0"
          />
          <textarea
            ref={contentRef}
            value={content}
            onChange={handleContentChange}
            placeholder="Start writing..."
            className="w-full min-h-[400px] sm:min-h-[500px] text-base sm:text-lg leading-relaxed bg-transparent border-none outline-none text-gray-700 dark:text-gray-300 placeholder-gray-400 resize-none focus:ring-0"
            style={{ fontFamily: "inherit" }}
          />
        </div>
      </div>
    </div>
  );
}
