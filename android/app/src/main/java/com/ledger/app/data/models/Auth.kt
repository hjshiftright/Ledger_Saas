package com.ledger.app.data.models

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class LoginRequest(
    val email: String,
    val password: String
)

@JsonClass(generateAdapter = true)
data class SignupRequest(
    val email: String,
    val password: String,
    val full_name: String? = null,
    val entity_type: String = "PERSONAL"
)

@JsonClass(generateAdapter = true)
data class AuthListResponse(
    val user_id: Int,
    val email: String,
    val tenants: List<TenantInfo>,
    val message: String
)

@JsonClass(generateAdapter = true)
data class TenantInfo(
    val tenant_id: String,
    val name: String,
    val entity_type: String,
    val role: String
)

@JsonClass(generateAdapter = true)
data class SelectTenantRequest(
    val tenant_id: String
)

@JsonClass(generateAdapter = true)
data class TokenResponse(
    val access_token: String,
    val token_type: String,
    val user_id: Int,
    val tenant_id: String,
    val role: String
)
