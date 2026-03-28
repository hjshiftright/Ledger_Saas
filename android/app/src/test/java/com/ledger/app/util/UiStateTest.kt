package com.ledger.app.util

import org.junit.Assert.*
import org.junit.Test

class UiStateTest {

    @Test
    fun loading_state_is_distinct() {
        val state: UiState<Nothing> = UiState.Loading
        assertTrue(state is UiState.Loading)
    }

    @Test
    fun success_state_carries_data() {
        val state = UiState.Success(listOf("a", "b"))
        assertTrue(state is UiState.Success)
        assertEquals(listOf("a", "b"), (state as UiState.Success).data)
    }

    @Test
    fun error_state_carries_message() {
        val state = UiState.Error("Network failed")
        assertTrue(state is UiState.Error)
        assertEquals("Network failed", (state as UiState.Error).message)
    }
}
