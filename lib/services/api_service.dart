import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:open_filex/open_filex.dart';

import '../models/session.dart';

class ApiService {
  
  static const String baseUrl = "http://127.0.0.1:8000";
    
  // =========================
  // LOGIN
  // =========================
  static Future<bool> login(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse("$baseUrl/login"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "username": username,
          "password": password,
        }),
      );

      final data = jsonDecode(response.body);

      if (data["success"] == true) {
        Session.userId        = data["user_id"];
        Session.username      = data["username"];
        Session.nombreCompleto = data["nombre_completo"] ?? "";
        Session.cedula        = data["cedula"] ?? "";
        Session.correo        = data["correo"] ?? "";
        Session.telefono      = data["telefono"] ?? "";
        // El backend devuelve "rol"; mapeamos a Session.role para compatibilidad
        Session.role   = data["rol"] ?? data["role"] ?? "";
        Session.status = data["status"] ?? "Disponible";
        return true;
      }

      return false;
    } catch (_) {
      return false;
    }
  }

  // =========================
  // REGISTER
  // =========================
  static Future<String?> register({
    required String username,
    required String password,
    required String nombreCompleto,
    required String cedula,
    required String correo,
    required String telefono,
    required String rol,
  }) async {
    try {
      final response = await http.post(
        Uri.parse("$baseUrl/register"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "username":         username,
          "password":         password,
          "nombre_completo":  nombreCompleto,
          "cedula":           cedula,
          "correo":           correo,
          "telefono":         telefono,
          "rol":              rol,
        }),
      );

      final data = jsonDecode(response.body);

      if (data["success"] == true) {
        return null; // null = sin error
      }

      return data["message"] ?? "No se pudo crear el usuario";
    } catch (_) {
      return "Error de conexión con el servidor";
    }
  }

  // =========================
  // CONDUCTORES
  // =========================
  static Future<List<dynamic>> getDrivers() async {
    try {
      final r = await http.get(Uri.parse("$baseUrl/drivers"));
      final data = jsonDecode(r.body);

      if (data["success"] == true) {
        return data["drivers"];
      }

      return [];
    } catch (_) {
      return [];
    }
  }

  // =========================
  // AFILIAR CONDUCTOR
  // =========================
  static Future<Map<String, dynamic>> assignDriver(
    int driverId,
    int vehicleId,
  ) async {
    try {
      final r = await http.post(
        Uri.parse("$baseUrl/assign-driver"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "driver_id": driverId,
          "vehicle_id": vehicleId,
        }),
      );

      return jsonDecode(r.body);
    } catch (_) {
      return {
        "success": false,
        "message": "Error de conexión",
      };
    }
  }

  // =========================
  // ASIGNAR VIAJE
  // =========================
  static Future<Map<String, dynamic>> assignTrip({
    required int tripId,
    required int driverId,
    required int vehicleId,
  }) async {
    try {
      final r = await http.post(
        Uri.parse("$baseUrl/assign-trip"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "trip_id": tripId,
          "driver_id": driverId,
          "vehicle_id": vehicleId,
        }),
      );

      return jsonDecode(r.body);
    } catch (_) {
      return {
        "success": false,
        "message": "Error de conexión",
      };
    }
  }

  // =========================
  // DETALLE VEHÍCULO
  // =========================
  static Future<Map<String, dynamic>?> getVehicleDetail(int vehicleId) async {
    try {
      final r = await http.get(
        Uri.parse("$baseUrl/vehicle/$vehicleId"),
      );

      final data = jsonDecode(r.body);

      if (data["success"] == true) {
        return data;
      }

      return null;
    } catch (_) {
      return null;
    }
  }

  // =========================
  // UPDATE VEHÍCULO
  // =========================
  static Future<Map<String, dynamic>> updateVehicle({
    required int vehicleId,
    required String placa,
    required String marca,
    required String modelo,
    required String color,
    required String apodo,
  }) async {
    try {
      final r = await http.put(
        Uri.parse("$baseUrl/vehicle/$vehicleId"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "placa": placa,
          "marca": marca,
          "modelo": modelo,
          "color": color,
          "apodo": apodo,
        }),
      );

      return jsonDecode(r.body);
    } catch (_) {
      return {
        "success": false,
        "message": "Error de conexión",
      };
    }
  }

  // =========================
  // DASHBOARD CONDUCTOR
  // =========================
  static Future<List<dynamic>> getDriverDashboard() async {
    try {
      final r = await http.get(
        Uri.parse("$baseUrl/driver/dashboard/${Session.userId}"),
      );

      final data = jsonDecode(r.body);

      if (data["success"] == true) {
        return data["vehicles"] ?? [];
      }

      return [];
    } catch (_) {
      return [];
    }
  }

  // =========================
  // KPI CONDUCTOR
  // =========================
  static Future<Map<String, dynamic>> getDriverKpis() async {
    try {
      final r = await http.get(
        Uri.parse("$baseUrl/driver/kpis/${Session.userId}"),
      );

      final data = jsonDecode(r.body);

      if (data["success"] == true) {
        return data["kpis"];
      }

      return {
        "completed": 0,
        "cancelled": 0,
        "total": 0,
      };
    } catch (_) {
      return {
        "completed": 0,
        "cancelled": 0,
        "total": 0,
      };
    }
  }

  // =========================
  // VIAJES CONDUCTOR
  // =========================
  static Future<List<dynamic>> getDriverTrips({
    String status = "Todos",
  }) async {
    try {
      final uri = Uri.parse(
        "$baseUrl/driver/trips/${Session.userId}?status=$status",
      );

      final r = await http.get(uri);
      final data = jsonDecode(r.body);

      if (data["success"] == true) {
        return data["trips"];
      }

      return [];
    } catch (_) {
      return [];
    }
  }

  static Future<bool> updateTripStatus(
    int tripId,
    String status,
  ) async {
    try {
      final r = await http.put(
        Uri.parse(
          "$baseUrl/driver/trips/$tripId/status?status=$status",
        ),
      );

      final data = jsonDecode(r.body);
      return data["success"] == true;
    } catch (_) {
      return false;
    }
  }

  // =========================
  // PROPIETARIO
  // =========================
  static Future<List<dynamic>> getVehicles() async {
    final r = await http.get(
      Uri.parse("$baseUrl/vehicles/${Session.userId}"),
    );
    return jsonDecode(r.body);
  }

  static Future<List<dynamic>> getTrips() async {
    final r = await http.get(
      Uri.parse("$baseUrl/trips/${Session.userId}"),
    );
    return jsonDecode(r.body);
  }

  static Future<bool> addVehicle(Map<String, dynamic> v) async {
    v["user_id"] = Session.userId;

    final r = await http.post(
      Uri.parse("$baseUrl/vehicles"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode(v),
    );

    return r.statusCode == 200;
  }

  static Future<Map<String, dynamic>> addVehicleDetailed(Map<String, dynamic> v) async {
    try {
      v["user_id"] = Session.userId;
      final r = await http.post(
        Uri.parse("$baseUrl/vehicles"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode(v),
      );
      final data = jsonDecode(r.body);
      if (data is Map<String, dynamic>) return data;
      return {"success": r.statusCode == 200};
    } catch (_) {
      return {"success": false, "message": "Error de conexión con el servidor"};
    }
  }

  static Future<bool> addTrip(Map<String, dynamic> t) async {
    t["user_id"] = Session.userId;

    final r = await http.post(
      Uri.parse("$baseUrl/trips"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode(t),
    );

    return r.statusCode == 200;
  }

  // =========================
  // REPORTES
  // =========================
  static Future<Map<String, dynamic>?> getReports() async {
    try {
      final r = await http.get(
        Uri.parse("$baseUrl/reports/${Session.userId}"),
      );

      final data = jsonDecode(r.body);

      if (data["success"] == true) {
        return data;
      }

      return null;
    } catch (_) {
      return null;
    }
  }

  // =========================
  // FACTURACIÓN
  // =========================
  static Future<Map<String, dynamic>?> getBilling() async {
    try {
      final r = await http.get(
        Uri.parse("$baseUrl/billing/${Session.userId}"),
      );

      final data = jsonDecode(r.body);

      if (data["success"] == true) {
        return data["billing"];
      }

      return null;
    } catch (_) {
      return null;
    }
  }

  // =========================
  // EXCEL URL
  // =========================
  static String getExcelUrl() {
    return "$baseUrl/reports/${Session.userId}/excel";
  }

  // =========================
  // DESCARGAR EXCEL
  // =========================
  static Future<void> downloadExcel() async {
    try {
      final dio = Dio();

      final dir = await getApplicationDocumentsDirectory();
      final filePath = "${dir.path}/reporte.xlsx";

      final url = "$baseUrl/reports/${Session.userId}/excel";

      await dio.download(url, filePath);

      await OpenFilex.open(filePath);
    } catch (e) {
      print("Error descargando Excel: $e");
    }
  }

  // =========================
  // ESTADO LABORAL CONDUCTOR
  // =========================
  static Future<bool> updateDriverStatus(String status) async {
    try {
      final r = await http.put(
        Uri.parse("$baseUrl/driver/status/${Session.userId}?status=$status"),
      );
      final data = jsonDecode(r.body);
      return data["success"] == true;
    } catch (_) {
      return false;
    }
  }

  // =========================
  // AFILIACIONES CONDUCTOR
  // =========================
  static Future<List<dynamic>> getDriverAffiliations() async {
    try {
      final r = await http.get(
        Uri.parse("$baseUrl/driver/affiliations/${Session.userId}"),
      );
      final data = jsonDecode(r.body);
      if (data["success"] == true) return data["affiliations"];
      return [];
    } catch (_) {
      return [];
    }
  }

  // =========================
  // REPORTES CON FILTROS
  // =========================
  static Future<Map<String, dynamic>?> getReportsFiltered({
    String? fechaInicio,
    String? fechaFin,
    String? estado,
  }) async {
    try {
      final params = <String, String>{};
      if (fechaInicio != null) params["fecha_inicio"] = fechaInicio;
      if (fechaFin != null) params["fecha_fin"] = fechaFin;
      if (estado != null && estado != "Todos") params["estado"] = estado;

      final uri = Uri.parse("$baseUrl/reports/${Session.userId}")
          .replace(queryParameters: params.isNotEmpty ? params : null);

      final r = await http.get(uri);
      final data = jsonDecode(r.body);
      if (data["success"] == true) return data;
      return null;
    } catch (_) {
      return null;
    }
  }

  // =========================
  // TRACTÁ — VEHÍCULOS SIN AFILIAR
  // =========================
  static Future<List<dynamic>> getVehiclesSinAfiliar() async {
    try {
      final r = await http.get(
        Uri.parse("$baseUrl/vehicles/${Session.userId}/sin-afiliar"),
      );
      final data = jsonDecode(r.body);
      if (data is List) return data;
      if (data["success"] == true) return data["vehicles"] ?? [];
      return [];
    } catch (_) {
      return [];
    }
  }

  // =========================
  // TRACTÁ — VEHÍCULOS AFILIADOS (con conductor)
  // =========================
  static Future<List<dynamic>> getVehiclesAfiliados() async {
    try {
      final r = await http.get(
        Uri.parse("$baseUrl/vehicles/${Session.userId}/afiliados"),
      );
      final data = jsonDecode(r.body);
      if (data is List) return data;
      if (data["success"] == true) return data["vehicles"] ?? [];
      return [];
    } catch (_) {
      return [];
    }
  }

  // =========================
  // TRACTÁ — VIAJES SIN ASIGNAR
  // =========================
  static Future<List<dynamic>> getTripsSinAsignar() async {
    try {
      final r = await http.get(
        Uri.parse("$baseUrl/trips/${Session.userId}/sin-asignar"),
      );
      final data = jsonDecode(r.body);
      if (data is List) return data;
      if (data["success"] == true) return data["trips"] ?? [];
      return [];
    } catch (_) {
      return [];
    }
  }

  // =========================
  // HISTORIAL DE TRACTÁS
  // =========================
  static Future<List<dynamic>> getTractas() async {
    try {
      final r = await http.get(
        Uri.parse("$baseUrl/tractas/${Session.userId}"),
      );
      final data = jsonDecode(r.body);
      if (data["success"] == true) return data["tractas"] ?? [];
      return [];
    } catch (_) {
      return [];
    }
  }

  // =========================
  // CONDUCTOR — TRACTÁS ORDENADAS
  // =========================
  static Future<List<dynamic>> getDriverTractas() async {
    try {
      final r = await http.get(
        Uri.parse("$baseUrl/driver/tractas/${Session.userId}"),
      );
      final data = jsonDecode(r.body);
      if (data["success"] == true) return data["tractas"] ?? [];
      return [];
    } catch (_) {
      return [];
    }
  }

  // =========================
  // PROPIETARIO — TODAS LAS AFILIACIONES
  // =========================
  static Future<List<dynamic>> getAllAffiliations() async {
    try {
      final r = await http.get(
        Uri.parse("$baseUrl/affiliations/owner/${Session.userId}"),
      );
      final data = jsonDecode(r.body);
      if (data["success"] == true) return data["affiliations"] ?? [];
      return [];
    } catch (_) {
      return [];
    }
  }

  // =========================
  // CONDUCTOR — PERFIL COMPLETO
  // =========================
  static Future<Map<String, dynamic>?> getDriverProfile(int driverId) async {
    try {
      final r = await http.get(
        Uri.parse("$baseUrl/driver/profile/$driverId"),
      );
      final data = jsonDecode(r.body) as Map<String, dynamic>;
      if (data["success"] == true) {
        final driver = data["driver"];
        if (driver is Map) {
          return Map<String, dynamic>.from(driver);
        }
      }
      return null;
    } catch (_) {
      return null;
    }
  }
}