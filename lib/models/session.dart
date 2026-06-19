class Session {
  static int?    userId;
  static String? username;
  static String? nombreCompleto;
  static String? cedula;
  static String? correo;
  static String? telefono;
  static String? role;   // mantiene compatibilidad con código existente
  static String? status; // mantiene compatibilidad con código existente

  static void clear() {
    userId        = null;
    username      = null;
    nombreCompleto = null;
    cedula        = null;
    correo        = null;
    telefono      = null;
    role          = null;
    status        = null;
  }
}