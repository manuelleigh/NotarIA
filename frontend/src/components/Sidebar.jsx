import React, { useState, useEffect, useContext } from "react";
import {
  ChevronsLeft,
  ChevronsRight,
  Plus,
  MessageSquare,
  FileText,
  Trash2,
  LogOut,
  Settings,
  HelpCircle,
  Sun,
  Moon,
  Home,
} from "lucide-react";
import { AuthContext } from "../contexts/AuthContext";

export function Sidebar({
  isSidebarOpen,
  toggleSidebar,
  onNewChat,
  onSelectChat,
  chats,
  activeChatId,
  onDeleteChat,
}) {
  const { logout } = useContext(AuthContext);

  const handleDeleteChat = (e, chatId) => {
    e.stopPropagation();
    if (window.confirm("¿Estás seguro de que quieres eliminar este chat?")) {
      onDeleteChat(chatId);
    }
  };

  return (
    <div
      className={`bg-slate-800 text-white flex flex-col transition-all duration-300 ${
        isSidebarOpen ? "w-64" : "w-20"
      }`}
    >
      {/* Header */}
      <div className="p-4 flex items-center justify-between">
        {isSidebarOpen && <h1 className="text-xl font-bold">LegalBot</h1>}
        <button onClick={toggleSidebar} className="p-2 hover:bg-slate-700 rounded">
          {isSidebarOpen ? <ChevronsLeft /> : <ChevronsRight />}
        </button>
      </div>

      {/* New Chat */}
      <div className="p-4">
        <button
          onClick={onNewChat}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded flex items-center justify-center"
        >
          <Plus className="h-5 w-5" />
          {isSidebarOpen && <span className="ml-2">Nuevo Chat</span>}
        </button>
      </div>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-4">
          <h2
            className={`text-xs font-semibold text-slate-400 ${
              isSidebarOpen ? "text-left" : "text-center"
            }`}
          >
            {isSidebarOpen ? "Historial" : "Chats"}
          </h2>
        </div>
        <ul className="mt-2">
          {chats.map((chat) => (
            <li key={chat.id} className="px-2 py-1">
              <div
                onClick={() => onSelectChat(chat.id)}
                className={`flex items-center justify-between p-2 rounded cursor-pointer ${
                  activeChatId === chat.id
                    ? "bg-slate-700"
                    : "hover:bg-slate-700/50"
                }`}
              >
                {isSidebarOpen ? (
                  <>
                    <div className="flex items-start gap-2">
                      <FileText
                        className={`h-4 w-4 mt-0.5 flex-shrink-0 ${
                          chat.contractGenerated
                            ? "text-green-500"
                            : "text-slate-400"
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="truncate text-sm">{chat.title}</p>
                        {chat.lastMessage && (
                          <p className="text-xs text-slate-500 truncate mt-0.5">
                            {chat.lastMessage}
                          </p>
                        )}
                        <p className="text-xs text-slate-600 mt-1">
                          {chat.messageCount > 0
                            ? `${chat.messageCount} mensajes`
                            : chat.lastMessage ? '1 mensaje' : 'Sin mensajes'}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={(e) => handleDeleteChat(e, chat.id)}
                      className="ml-2 p-1 text-slate-400 hover:text-white hover:bg-slate-600 rounded"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </>
                ) : (
                  <MessageSquare className="h-6 w-6 text-slate-300 mx-auto" />
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>

      {/* User Menu */}
      <div className="p-4 border-t border-slate-700">
        <div className="flex items-center">
          <div className="w-10 h-10 rounded-full bg-slate-600 flex items-center justify-center font-bold">
            U
          </div>
          {isSidebarOpen && (
            <div className="ml-3">
              <p className="font-semibold">Usuario</p>
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
