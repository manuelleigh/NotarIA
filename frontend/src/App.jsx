import React, { useState, useEffect, useCallback } from "react";
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ChatInterface } from "./components/ChatInterface";
import { Sidebar } from "./components/Sidebar";
import { ContractPreview } from "./components/ContractPreview";
import { Auth } from "./components/Auth";
import { ForgotPassword } from "./components/ForgotPassword";
import { ResetPassword } from "./components/ResetPassword";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { getChatHistory, getChatDetail, sendChatMessageStreaming } from "./services/apiService";
import { toast } from "sonner";
import { Toaster } from "./components/ui/sonner";

function LoadingScreen() {
  return (
    <div className="flex items-center justify-center h-screen bg-slate-100">
      <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

function MainApp() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <LoadingScreen />;
  return (
    <Router>
      <Routes>
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/*" element={isAuthenticated ? <ChatApp /> : <Auth />} />
      </Routes>
    </Router>
  );
}

function ChatApp() {
  const { apiKey } = useAuth();
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [showContractPreview, setShowContractPreview] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 1024); // Default to open on desktop
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  const currentChat = chats.find((chat) => chat.id === activeChatId);

  // Load initial chat history
  const loadHistory = useCallback(async () => {
    if (!apiKey) return;
    setIsLoadingHistory(true);
    try {
      const history = await getChatHistory(apiKey);
      const loadedChats = history.map((item) => ({
        id: `chat-${item.chat_id}`,
        title: item.nombre,
        messages: [],
        contractGenerated: item.contrato !== null,
        lastMessage: item.ultimo_mensaje,
        apiChatId: item.chat_id,
        contexto: item.metadatos || {},
      }));
      setChats(loadedChats);
    } catch (error) {
      toast.error("Error al cargar historial: " + error.message);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [apiKey]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // Handle selecting a chat from the sidebar
  const handleSelectChat = async (chatId) => {
    const selectedChat = chats.find((c) => c.id === chatId);
    if (!selectedChat) return;

    // Set active chat immediately for UI responsiveness
    setActiveChatId(chatId);

    // Decide if we need to show the preview panel
    setShowContractPreview(selectedChat.contractGenerated);

    // If messages are already loaded, don't re-fetch
    if (selectedChat.messages && selectedChat.messages.length > 0) {
      return;
    }

    // If it's a new chat placeholder, do nothing
    if (!selectedChat.apiChatId) {
      return;
    }
    
    // Fetch full chat details
    try {
      const detail = await getChatDetail(selectedChat.apiChatId, apiKey);
      const messages = detail.mensajes.map((msg) => ({
        id: `msg-${msg.id}`,
        role: msg.remitente === "usuario" ? "user" : "assistant",
        content: msg.contenido,
        createdAt: new Date(msg.fecha_creacion),
      }));

      // Update the specific chat with its full messages and contract status
      setChats((prev) =>
        prev.map((c) =>
          c.id === chatId
            ? { ...c, messages, contractGenerated: detail.contrato !== null }
            : c
        )
      );
       // Ensure the preview state is correct after fetching details
      setShowContractPreview(detail.contrato !== null);
    } catch (error) {
      toast.error("Error al cargar la conversación: " + error.message);
    }
  };

  // Handle creating a new chat
  const handleNewChat = () => {
    const newChat = {
      id: `new-${Date.now()}`,
      title: "Nuevo Contrato",
      messages: [
        {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content: "Bienvenido. ¿Qué contrato necesita?",
          createdAt: new Date(),
        },
      ],
      contractGenerated: false, 
      contexto: {},
    };
    setChats([newChat, ...chats]);
    setActiveChatId(newChat.id);
    setShowContractPreview(false);
  };

  // Handle sending a message (streaming)
  const handleSendMessage = async (content) => {
    if (!currentChat) return;

    const userMessage = {
      id: `${Date.now()}-user`,
      role: "user",
      content,
      createdAt: new Date(),
    };
    
    const updatedMessages = [...currentChat.messages, userMessage];
    setChats((prev) =>
      prev.map((chat) => (chat.id === activeChatId ? { ...chat, messages: updatedMessages } : chat))
    );

    const assistantMessageId = `${Date.now()}-ai`;
    try {
      await sendChatMessageStreaming(currentChat.contexto, content, (chunk) => {
        setChats((prev) => {
          return prev.map((chat) => {
            if (chat.id !== activeChatId) return chat;

            let newMessages = [...chat.messages];
            let newContext = chat.contexto;
            let contractGenerated = chat.contractGenerated;

            if (chunk.text) {
              const lastMessage = newMessages[newMessages.length - 1];
              if (lastMessage?.id === assistantMessageId) {
                newMessages[newMessages.length - 1] = { ...lastMessage, content: lastMessage.content + chunk.text };
              } else {
                newMessages.push({ id: assistantMessageId, role: "assistant", content: chunk.text, createdAt: new Date() });
              }
            }
            if (chunk.context) {
              newContext = chunk.context;
            }
            if (chunk.contract) {
                contractGenerated = true;
                setShowContractPreview(true); // Automatically show preview when contract is generated
            }

            return { ...chat, messages: newMessages, contexto: newContext, contractGenerated };
          });
        });
      });

    } catch (error) {
      toast.error("Error en la comunicación con el asistente: " + error.message);
    }
  };

  return (
    <div className="flex h-screen bg-slate-100 text-slate-800">
      <Sidebar
        chats={chats}
        activeChat={activeChatId || ""}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        // isLoading={isLoadingHistory} // This prop is not used in the new Sidebar
      />
      <main className="flex-1 flex flex-col overflow-hidden">
        <ChatInterface
          chat={currentChat}
          onSendMessage={handleSendMessage}
          onTogglePreview={() => setShowContractPreview(!showContractPreview)}
          showPreview={showContractPreview}
        />
        {showContractPreview && currentChat?.contractGenerated && (
          <div className="lg:w-1/2 xl:w-2/5 border-l border-slate-200 hidden lg:flex flex-col">
            <ContractPreview chat={currentChat} onClose={() => setShowContractPreview(false)} />
          </div>
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
      <Toaster />
    </AuthProvider>
  );
}
