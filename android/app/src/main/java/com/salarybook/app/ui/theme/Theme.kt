package com.salarybook.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val Primary = Color(0xFFFF6B35)
val PrimaryContainer = Color(0xFFFFD9C7)
val OnPrimary = Color.White
val OnPrimaryContainer = Color(0xFF572000)
val Secondary = Color(0xFF77574A)
val SecondaryContainer = Color(0xFFFFDBC9)
val OnSecondaryContainer = Color(0xFF2C160C)
val Background = Color(0xFFFFF8F5)
val Surface = Color(0xFFFFF8F5)
val SurfaceVariant = Color(0xFFF5DEDA)
val OnBackground = Color(0xFF211A17)
val OnSurface = Color(0xFF211A17)
val OnSurfaceVariant = Color(0xFF52443E)
val Outline = Color(0xFF85736C)
val Success = Color(0xFF2E7D32)
val Danger = Color(0xFFC62828)
val CardBg = Color(0xFFFFFFFF)

val DarkPrimary = Color(0xFFFFB59B)
val DarkPrimaryContainer = Color(0xFF58331F)
val DarkOnPrimaryContainer = Color(0xFFFFDBC9)
val DarkBackground = Color(0xFF181210)
val DarkSurface = Color(0xFF181210)
val DarkSurfaceVariant = Color(0xFF52443E)
val DarkOnSurface = Color(0xFFF0DFD9)
val DarkOnSurfaceVariant = Color(0xFFD7C3BC)
val DarkCardBg = Color(0xFF241C19)

private val LightColors = lightColorScheme(
    primary = Primary,
    onPrimary = OnPrimary,
    primaryContainer = PrimaryContainer,
    onPrimaryContainer = OnPrimaryContainer,
    secondary = Secondary,
    secondaryContainer = SecondaryContainer,
    onSecondaryContainer = OnSecondaryContainer,
    background = Background,
    surface = Surface,
    onBackground = OnBackground,
    onSurface = OnSurface,
    surfaceVariant = SurfaceVariant,
    onSurfaceVariant = OnSurfaceVariant,
    outline = Outline,
)

private val DarkColors = darkColorScheme(
    primary = DarkPrimary,
    onPrimary = Color(0xFF4A1D08),
    primaryContainer = DarkPrimaryContainer,
    onPrimaryContainer = DarkOnPrimaryContainer,
    secondary = Color(0xFFE7BFA8),
    secondaryContainer = Color(0xFF5C3F33),
    onSecondaryContainer = Color(0xFFFFDBC9),
    background = DarkBackground,
    surface = DarkSurface,
    onBackground = Color(0xFFF0DFD9),
    onSurface = DarkOnSurface,
    surfaceVariant = DarkSurfaceVariant,
    onSurfaceVariant = DarkOnSurfaceVariant,
    outline = Color(0xFF9C8B83),
)

@Composable
fun SalaryTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = Typography,
        content = content,
    )
}
