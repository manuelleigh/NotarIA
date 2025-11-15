const API_BASE_URL = "http://127.0.0.1:5000";

async function handleResponse(response) {
  if (!response.ok) {
    if (response.status === 401) throw new Error("Token requerido");
    if (response.status === 403) throw new Error("Usuario no autorizado");
    if (response.status === 404) throw new Error("Recurso no encontrado");
    throw new Error("Error en la solicitud a la API");
  }
  return response.json();
}

export async function getChatHistory(apiKey) {
  const response = await fetch(`${API_BASE_URL}/chat/historial`, {
    headers: { Authorization: `Bearer ${apiKey}` },
  });
  const data = await handleResponse(response);
  return data.data;
}

export async function getChatDetail(chatId, apiKey) {
  const response = await fetch(`${API_BASE_URL}/chat/${chatId}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
  });
  return handleResponse(response);
}

export async function sendChatMessage(mensaje, apiKey, chatId, nombre) {
  const body = { mensaje, chat_id: chatId, nombre };
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(body),
  });
  return handleResponse(response);
}

export async function sendChatMessageStreaming(contexto, message, onChunk) {
  try {
    const response = await fetch(`${API_BASE_URL}/chat/streaming`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contexto, message }),
    });

    if (!response.body) return;

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      
      // No procesar el buffer, simplemente pasar el chunk
      onChunk(buffer);
      buffer = ""; // Limpiar el buffer después de cada chunk
    }

  } catch (error) {
    console.error("Error en la comunicación streaming:", error);
    throw error;
  }
}

export async function getContractDocument(chatId) {
  const response = await fetch(`${API_BASE_URL}/chat/documento?chat_id=${chatId}`);
  if (!response.ok) {
    if (response.status === 404) throw new Error("Chat no encontrado");
    throw new Error("Error al obtener el documento");
  }
  return response.text();
}
