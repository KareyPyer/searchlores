# searchlores/core/context.py
# Extension pour supporter les plugins avancés

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class InvestigationContext:
    """Contexte partagé d'une investigation."""

    prompt: str
    findings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    layers: List[Dict[str, Any]] = field(default_factory=list)
    lore_applied: Optional[str] = None

    def __post_init__(self):
        """Initialisation post-création."""
        if not self.metadata:
            self.metadata = {
                "timestamp": datetime.now().isoformat(),
                "findings_count": 0
            }

    def add_finding(self, key: str, value: Any) -> None:
        """Ajoute une trouvaille de manière structurée."""
        if key not in self.findings:
            self.findings[key] = []
        if isinstance(value, list):
            self.findings[key].extend(value)
        else:
            self.findings[key].append(value)
        self.metadata["findings_count"] = len(self.findings)

    def add_layer(self, layer_name: str, data: Dict[str, Any]) -> None:
        """Ajoute une couche d'analyse."""
        self.layers.append({
            "name": layer_name,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le contexte en dictionnaire."""
        return {
            "prompt": self.prompt,
            "findings": self.findings,
            "metadata": self.metadata,
            "errors": self.errors,
            "layers": self.layers
        }

    def merge(self, other: 'InvestigationContext') -> None:
        """Fusionne un autre contexte dans celui-ci."""
        for key, value in other.findings.items():
            if key not in self.findings:
                self.findings[key] = []
            if isinstance(value, list):
                self.findings[key].extend(value)
            else:
                self.findings[key].append(value)

        self.errors.extend(other.errors)
        self.layers.extend(other.layers)

        # Mettre à jour les métadonnées
        self.metadata["findings_count"] = len(self.findings)
        self.metadata["last_merge"] = datetime.now().isoformat()
