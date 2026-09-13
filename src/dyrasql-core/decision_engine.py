#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Decision Engine - algoritmo de decisao de roteamento
S = w1 * fv + w2 * fc + w3 * fh
"""

import logging
import math
import os

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Calcula o score e seleciona o cluster apropriado"""

    def __init__(self):
        self.w1 = float(os.getenv("DYRASQL_WEIGHT_VOLUME", "0.5"))
        self.w2 = float(os.getenv("DYRASQL_WEIGHT_COMPLEXITY", "0.3"))
        self.w3 = float(os.getenv("DYRASQL_WEIGHT_HISTORICAL", "0.2"))
        self.small_threshold = float(os.getenv("DYRASQL_SMALL_THRESHOLD", "0.3"))
        self.medium_threshold = float(
            os.getenv("DYRASQL_MEDIUM_THRESHOLD", "0.7")
        )

        total_weight = self.w1 + self.w2 + self.w3
        if abs(total_weight - 1.0) > 0.1:
            logger.warning(
                "Soma dos pesos (%.2f) difere de 1.0. Considere ajustar os pesos.",
                total_weight,
            )

        logger.info(
            "Decision Engine: w1=%.2f w2=%.2f w3=%.2f | small < %.2f | medium <= %.2f | large > %.2f",
            self.w1,
            self.w2,
            self.w3,
            self.small_threshold,
            self.medium_threshold,
            self.medium_threshold,
        )

    def decide(self, query, fingerprint, metadata, complexity, history_manager):
        fv = self._calculate_volume_factor(metadata)
        fc = self._calculate_complexity_factor(complexity)
        fh = history_manager.get_historical_factor(fingerprint, query)
        score = self.w1 * fv + self.w2 * fc + self.w3 * fh
        cluster = self._select_cluster(score)
        decision = {
            "cluster": cluster,
            "score": score,
            "factors": {
                "volume": fv,
                "complexity": fc,
                "historical": fh,
            },
        }
        logger.info("Decisao calculada: score=%.3f, cluster=%s", score, cluster)
        return decision

    def _calculate_volume_factor(self, metadata):
        if not metadata:
            return 0.5

        total_size_bytes = sum(m.get("total_size_bytes", 0) for m in metadata.values())
        total_rows = sum(m.get("total_records", 0) for m in metadata.values())
        total_size_gb = total_size_bytes / (1024**3)
        max_size_gb = 1000
        max_rows = 1e9
        optimization_factor = 0.1

        # Valores efetivos (garantindo mínimos para log)
        effective_size_gb = max(0.001, total_size_gb)
        effective_rows = max(1, total_rows)

        # Normalização logarítmica conforme artigo (Equação 2)
        # fv = (log(Te) / log(Tmax) * 0.6 + log(Re) / log(Rmax) * 0.4) * (1 - Fo)
        normalized_size = min(1.0, math.log(effective_size_gb) / math.log(max_size_gb))
        normalized_rows = min(1.0, math.log(effective_rows) / math.log(max_rows))
        
        # Pesos conforme artigo: 0.6 para tamanho, 0.4 para linhas
        fv = (normalized_size * 0.6 + normalized_rows * 0.4) * (1 - optimization_factor)
        fv = max(0, min(1, fv))
        
        logger.debug(
            "Fator volume: size=%.2fGB rows=%.0f normalized_size=%.3f normalized_rows=%.3f fv=%.3f",
            total_size_gb,
            total_rows,
            normalized_size,
            normalized_rows,
            fv,
        )
        return fv

    def _calculate_complexity_factor(self, complexity):
        joins = complexity.get("joins", 0)
        aggregations = complexity.get("aggregations", 0)
        subqueries = complexity.get("subqueries", 0)
        partitioned_filters = complexity.get("partitioned_filters", 0)
        non_partitioned_filters = complexity.get("non_partitioned_filters", 0)
        complexity_limit = 2.0
        fc = (
            joins * 0.2
            + aggregations * 0.15
            + subqueries * 0.25
            + partitioned_filters * 0.02
            + non_partitioned_filters * 0.1
        ) / complexity_limit
        fc = max(0, min(1, fc))
        logger.debug(
            "Fator complexidade: joins=%s aggs=%s fc=%.3f", joins, aggregations, fc
        )
        return fc

    def _select_cluster(self, score):
        if score < self.small_threshold:
            return "small"
        if score <= self.medium_threshold:
            return "medium"
        return "large"
