const API_BASE_URL = "http://127.0.0.1:5000";

async function handleResponse(response) {
  if (!response.ok) {
    const errorBody = await response.text(); // Leer el cuerpo para más contexto
    console.error("API Error Response:", errorBody);

    if (response.status === 401) throw new Error("Token de autenticación inválido o expirado.");
    if (response.status === 403) throw new Error("No tienes permiso para realizar esta acción.");
    if (response.status === 404) throw new Error("El recurso solicitado no fue encontrado.");
    
    throw new Error(`Error en la solicitud a la API: ${response.statusText}`);
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
    const separator = "CTX_UPDATE::";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        // Procesar cualquier remanente en el buffer al final del stream
        if (buffer) onChunk({ text: buffer });
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Buscar si el separador está en el buffer
      const separatorIndex = buffer.indexOf(separator);

      if (separatorIndex !== -1) {
        // Parte 1: Texto antes del separador
        const textPart = buffer.substring(0, separatorIndex);
        if (textPart) {
          onChunk({ text: textPart });
        }

        // Parte 2: El objeto JSON después del separador
        const jsonString = buffer.substring(separatorIndex + separator.length);
        try {
          const contextUpdate = JSON.parse(jsonString);
          onChunk({ context: contextUpdate });
        } catch (e) {
          console.error("Error al parsear el JSON del contexto:", e, "String recibido:", jsonString);
        }

        // El stream ha terminado, no debería haber más datos
        buffer = "";
        break; // Salir del bucle porque el contexto es la señal final

      } else {
        // Si no se encuentra el separador, todo es texto por ahora
        onChunk({ text: buffer });
        buffer = ""; // Limpiar el buffer después de enviar
      }
    }

  } catch (error) {
    console.error("Error en la comunicación streaming:", error);
    throw error; // Re-lanzar para que pueda ser manejado por el componente
  }
}

export async function getContractDocument(chatId) {
  const response = await fetch(`${API_BASE_URL}/chat/documento?chat_id=${chatId}`);
  if (!response.ok) {
    const errorBody = await response.text();
    console.error("Error al obtener documento:", errorBody);
    if (response.status === 404) throw new Error("Documento o chat no encontrado.");
    throw new Error("Error al obtener el documento del contrato.");
  }
  // Devuelve el HTML como texto plano
  return response.text();
}
