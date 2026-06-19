import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/liquid_background.dart';
import '../widgets/liquid_glass_card.dart';
import 'welcome_screen.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey     = GlobalKey<FormState>();
  final userCtrl     = TextEditingController();
  final passCtrl     = TextEditingController();
  final confirmCtrl  = TextEditingController();
  final nombreCtrl   = TextEditingController();
  final cedulaCtrl   = TextEditingController();
  final correoCtrl   = TextEditingController();
  final telefonoCtrl = TextEditingController();

  String _rolSeleccionado = "propietario";
  bool   _obscurePass     = true;
  bool   _obscureConfirm  = true;
  String? message;

  @override
  void dispose() {
    userCtrl.dispose();
    passCtrl.dispose();
    confirmCtrl.dispose();
    nombreCtrl.dispose();
    cedulaCtrl.dispose();
    correoCtrl.dispose();
    telefonoCtrl.dispose();
    super.dispose();
  }

  Future<void> createUser() async {
    if (!_formKey.currentState!.validate()) return;

    final error = await ApiService.register(
      username:        userCtrl.text.trim(),
      password:        passCtrl.text.trim(),
      nombreCompleto:  nombreCtrl.text.trim(),
      cedula:          cedulaCtrl.text.trim(),
      correo:          correoCtrl.text.trim(),
      telefono:        telefonoCtrl.text.trim(),
      rol:             _rolSeleccionado,
    );

    if (!mounted) return;

    if (error == null) {
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const WelcomeScreen()),
        (route) => false,
      );
    } else {
      setState(() => message = error);
    }
  }

  // Campo de texto reutilizable
  Widget _field({
    required TextEditingController ctrl,
    required String label,
    required IconData icon,
    bool obscure = false,
    bool? obscureState,
    VoidCallback? toggleObscure,
    TextInputType keyboardType = TextInputType.text,
    String? Function(String?)? validator,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextFormField(
        controller: ctrl,
        obscureText: obscure ? (obscureState ?? true) : false,
        keyboardType: keyboardType,
        decoration: InputDecoration(
          labelText: label,
          prefixIcon: Icon(icon, size: 20),
          suffixIcon: obscure
              ? IconButton(
                  icon: Icon(
                    (obscureState ?? true) ? Icons.visibility_off : Icons.visibility,
                    size: 20,
                    color: Colors.white54,
                  ),
                  onPressed: toggleObscure,
                )
              : null,
        ),
        validator: validator ??
            (v) => v == null || v.trim().isEmpty ? "$label obligatorio" : null,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: LiquidBackground(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(vertical: 32),
            child: SizedBox(
              width: 460,
              child: LiquidGlassCard(
                child: Padding(
                  padding: const EdgeInsets.all(30),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // ── Botón atrás ──
                        Align(
                          alignment: Alignment.centerLeft,
                          child: IconButton(
                            icon: const Icon(Icons.arrow_back),
                            onPressed: () => Navigator.pushReplacement(
                              context,
                              MaterialPageRoute(
                                builder: (_) => const WelcomeScreen(),
                              ),
                            ),
                          ),
                        ),

                        const Text(
                          "Crear cuenta",
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 22),

                        // ── Campos personales ──
                        _field(
                          ctrl: nombreCtrl,
                          label: "Nombre completo",
                          icon: Icons.person_outline,
                        ),
                        _field(
                          ctrl: cedulaCtrl,
                          label: "Cédula",
                          icon: Icons.badge_outlined,
                          keyboardType: TextInputType.number,
                          validator: (v) {
                            if (v == null || v.trim().isEmpty) return "Cédula obligatoria";
                            if (v.trim().length < 5) return "Cédula inválida";
                            return null;
                          },
                        ),
                        _field(
                          ctrl: correoCtrl,
                          label: "Correo electrónico",
                          icon: Icons.email_outlined,
                          keyboardType: TextInputType.emailAddress,
                          validator: (v) {
                            if (v == null || v.trim().isEmpty) return "Correo obligatorio";
                            if (!v.contains("@") || !v.contains(".")) return "Correo inválido";
                            return null;
                          },
                        ),
                        _field(
                          ctrl: telefonoCtrl,
                          label: "Teléfono",
                          icon: Icons.phone_outlined,
                          keyboardType: TextInputType.phone,
                          validator: (v) {
                            if (v == null || v.trim().isEmpty) return "Teléfono obligatorio";
                            if (v.trim().length < 7) return "Teléfono inválido";
                            return null;
                          },
                        ),

                        const Divider(height: 24),

                        // ── Credenciales ──
                        _field(
                          ctrl: userCtrl,
                          label: "Usuario",
                          icon: Icons.alternate_email,
                          validator: (v) {
                            if (v == null || v.trim().isEmpty) return "Usuario obligatorio";
                            if (v.trim().length < 3) return "Mínimo 3 caracteres";
                            return null;
                          },
                        ),
                        _field(
                          ctrl: passCtrl,
                          label: "Contraseña",
                          icon: Icons.lock_outline,
                          obscure: true,
                          obscureState: _obscurePass,
                          toggleObscure: () => setState(() => _obscurePass = !_obscurePass),
                          validator: (v) {
                            if (v == null || v.trim().isEmpty) return "Contraseña obligatoria";
                            if (v.trim().length < 4) return "Mínimo 4 caracteres";
                            return null;
                          },
                        ),
                        _field(
                          ctrl: confirmCtrl,
                          label: "Confirmar contraseña",
                          icon: Icons.lock_outline,
                          obscure: true,
                          obscureState: _obscureConfirm,
                          toggleObscure: () => setState(() => _obscureConfirm = !_obscureConfirm),
                          validator: (v) => v != passCtrl.text
                              ? "Las contraseñas no coinciden"
                              : null,
                        ),

                        const Divider(height: 24),

                        // ── Selector de rol ──
                        const Text(
                          "Tipo de cuenta",
                          style: TextStyle(
                            fontSize: 13,
                            color: Colors.white70,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(
                              child: _RolOption(
                                label: "Propietario",
                                icon: Icons.business_center_outlined,
                                selected: _rolSeleccionado == "propietario",
                                onTap: () => setState(() => _rolSeleccionado = "propietario"),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: _RolOption(
                                label: "Conductor",
                                icon: Icons.local_shipping_outlined,
                                selected: _rolSeleccionado == "conductor",
                                onTap: () => setState(() => _rolSeleccionado = "conductor"),
                              ),
                            ),
                          ],
                        ),

                        // ── Mensaje de error ──
                        if (message != null)
                          Padding(
                            padding: const EdgeInsets.only(top: 14),
                            child: Text(
                              message!,
                              textAlign: TextAlign.center,
                              style: const TextStyle(
                                color: Colors.redAccent,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),

                        const SizedBox(height: 20),

                        // ── Botón crear ──
                        ElevatedButton(
                          onPressed: createUser,
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 14),
                          ),
                          child: const Text(
                            "Crear cuenta",
                            style: TextStyle(fontSize: 16),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────
// Widget interno para seleccionar el rol
// ─────────────────────────────────────────
class _RolOption extends StatelessWidget {
  final String    label;
  final IconData  icon;
  final bool      selected;
  final VoidCallback onTap;

  const _RolOption({
    required this.label,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: selected
              ? Colors.white.withOpacity(0.18)
              : Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: selected ? Colors.white60 : Colors.white24,
            width: selected ? 1.5 : 1,
          ),
        ),
        child: Column(
          children: [
            Icon(icon, color: selected ? Colors.white : Colors.white54, size: 26),
            const SizedBox(height: 6),
            Text(
              label,
              style: TextStyle(
                color: selected ? Colors.white : Colors.white54,
                fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
                fontSize: 13,
              ),
            ),
          ],
        ),
      ),
    );
  }
}