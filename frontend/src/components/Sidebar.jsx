import React from "react";
import {
  ChevronsLeft,
  ChevronsRight,
  Plus,
  MessageSquare,
  FileText,
  Trash2,
  LogOut,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

export function Sidebar({
  isOpen,
  onToggle,
  onNewChat,
  onSelectChat,
  chats,
  activeChat,
  // onDeleteChat, // This prop is not being passed from App.jsx, let's remove it for now
}) {
  const { logout } = useAuth();

  const handleDeleteChat = (e, chatId) => {
    e.stopPropagation();
    // This should be handled by a prop from App.jsx, but it's missing.
    // For now, we'll add a placeholder.
    if (window.confirm("La función para eliminar chats aún no está conectada.")) {
      // onDeleteChat(chatId);
    }
  };

  return (
    <div
      className={`bg-slate-800 text-white flex flex-col transition-all duration-300 ${
        isOpen ? "w-72" : "w-20"
      }`}
    >
      {/* Header */}
      <div className="p-4 flex items-center justify-between">
        {isOpen && <h1 className="text-xl font-bold">LegalBot</h1>}
        <button onClick={onToggle} className="p-2 hover:bg-slate-700 rounded">
          {isOpen ? <ChevronsLeft /> : <ChevronsRight />}
        </button>
      </div>

      {/* New Chat */}
      <div className="p-4">
        <button
          onClick={onNewChat}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded flex items-center justify-center"
        >
          <Plus className="h-5 w-5" />
          {isOpen && <span className="ml-2">Nuevo Chat</span>}
        </button>
      </div>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-4">
          <h2
            className={`text-xs font-semibold text-slate-400 ${
              isOpen ? "text-left" : "text-center"
            }`}
          >
            {isOpen ? "Historial" : "Chats"}
          </h2>
        </div>
        <ul className="mt-2">
          {chats.map((chat) => (
            <li key={chat.id} className="px-2 py-1">
              <div
                onClick={() => onSelectChat(chat.id)}
                className={`flex items-center justify-between p-2 rounded cursor-pointer ${
                  activeChat === chat.id
                    ? "bg-slate-700"
                    : "hover:bg-slate-700/50"
                }`}
              >
                {isOpen ? (
                  <>
                    <div className="flex items-start gap-2 flex-1 min-w-0">
                      <FileText
                        className={`h-4 w-4 mt-1 flex-shrink-0 ${
                          chat.contractGenerated
                            ? "text-green-500"
                            : "text-slate-400"
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="truncate text-sm font-semibold text-slate-100">{chat.title}</p>
                        {chat.lastMessage && (
                          <p className="text-xs text-slate-400 truncate mt-1">
                            {chat.lastMessage}
                          </p>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={(e) => handleDeleteChat(e, chat.id)}
                      className="ml-2 p-1 text-slate-500 hover:text-white hover:bg-slate-600 rounded opacity-50 hover:opacity-100"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </>
                ) : (
                  <div className="relative w-full flex justify-center">
                     <MessageSquare className="h-6 w-6 text-slate-300" />
                     {chat.contractGenerated && <div className="absolute bottom-0 right-1.5 w-2 h-2 rounded-full bg-green-500 border-2 border-slate-700"></div>}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>

      {/* User Menu */}
      <div className="p-4 border-t border-slate-700">
        <div className="flex items-center">
          <div className="w-10 h-10 rounded-full bg-slate-600 flex items-center justify-center font-bold text-slate-300">
            U
          </div>
          {isOpen && (
            <div className="ml-3">
              <p className="font-semibold text-slate-200">Usuario</p>
              <button
                onClick={logout}
                className="text-xs text-slate-400 hover:text-white"
              >
                Cerrar sesión
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
