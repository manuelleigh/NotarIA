import React from "react";
import { FileText, User } from "lucide-react";

export function ChatMessage({ message }) {
  const isAssistant = message.role === "assistant";

  // A defensive check, in case message is somehow undefined.
  if (!message) {
    return null;
  }

  return (
    <div
      className={`flex items-start gap-3 ${
        !isAssistant ? "flex-row-reverse" : ""
      }`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isAssistant ? "bg-blue-600" : "bg-slate-700"
        }`}
      >
        {isAssistant ? (
          <FileText className="h-4 w-4 text-white" />
        ) : (
          <User className="h-4 w-4 text-white" />
        )}
      </div>

      {/* Message content */}
      <div className={`flex-1 ${!isAssistant ? "flex justify-end" : ""}`}>
        <div
          className={`rounded-2xl p-4 max-w-[85%] ${
            isAssistant
              ? "bg-slate-100 rounded-tl-sm text-slate-900"
              : "bg-blue-600 rounded-tr-sm text-white"
          }`}
        >
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
          {/* Conditionally render the timestamp only if it exists */}
          {message.createdAt && (
            <div
              className={`text-xs mt-2 ${
                isAssistant ? "text-slate-500" : "text-blue-100"
              }`}
            >
              {/* Ensure createdAt is a Date object before calling toLocaleTimeString */}
              {new Date(message.createdAt).toLocaleTimeString("es-ES", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
