"use client";

import { useState, useEffect, useRef } from "react";
import { Trash2 } from "lucide-react";
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
  const titleRef = useRef<HTMLInputElement>(null);
  const contentRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setTitle(note.title);
    setContent(note.content);
  }, [note.id, note.title, note.content]);

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

  return (
    <div className="flex-1 flex flex-col bg-white dark:bg-gray-900">
      {/* Toolbar */}
      <div className="border-b border-gray-200 dark:border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {formatDate(note.updatedAt)}
          </span>
        </div>
        <button
          onClick={handleDelete}
          className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          aria-label="Delete note"
        >
          <Trash2 className="w-5 h-5 text-red-500" />
        </button>
      </div>

      {/* Editor */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="max-w-4xl mx-auto">
          <input
            ref={titleRef}
            type="text"
            value={title}
            onChange={handleTitleChange}
            placeholder="Untitled Note"
            className="w-full text-4xl font-bold mb-6 bg-transparent border-none outline-none text-gray-900 dark:text-white placeholder-gray-400 resize-none"
          />
          <textarea
            ref={contentRef}
            value={content}
            onChange={handleContentChange}
            placeholder="Start writing..."
            className="w-full min-h-[500px] text-lg leading-relaxed bg-transparent border-none outline-none text-gray-700 dark:text-gray-300 placeholder-gray-400 resize-none"
            style={{ fontFamily: "inherit" }}
          />
        </div>
      </div>
    </div>
  );
}
