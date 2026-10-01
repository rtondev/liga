"""Funções oxigenadas que viram as faces do dominó.

A legenda do projeto fixa o número de cada função:
ácido 0, éster 1, éter 2, fenol 3, álcool 4, cetona 5, aldeído 6.
"""

FUNCTIONS = {
    0: {
        "tile": "Ácido",
        "name": "Ácido carboxílico",
        "formula": "R–COOH",
        "struct": "  O\n  ‖\nR–C–OH",
        "suffix": "ácido …oico",
        "example": "Ácido etanoico",
        "detail": "A carboxila junta carbonila e hidroxila no mesmo carbono. No dominó ela é a face 0, sem pintas.",
    },
    1: {
        "tile": "Éster",
        "name": "Éster",
        "formula": "R–COO–R",
        "struct": "   O\n   ‖\nR–C–OR",
        "suffix": "…oato de …ila",
        "example": "Etanoato de metila",
        "detail": "Deriva da troca do hidrogênio da carboxila por um grupo carbônico. Face 1 do dominó.",
    },
    2: {
        "tile": "Éter",
        "name": "Éter",
        "formula": "R–O–R",
        "struct": "R–O–R",
        "suffix": "alcóxi-alcano",
        "example": "Metoxietano",
        "detail": "O oxigênio fica entre dois carbonos, sem carbonila. Face 2 do dominó.",
    },
    3: {
        "tile": "Fenol",
        "name": "Fenol",
        "formula": "Ar–OH",
        "struct": "Ph–OH",
        "suffix": "fenol / hidróxi",
        "example": "Fenol",
        "detail": "A hidroxila está ligada direto ao anel aromático. Não é álcool. Face 3 do dominó.",
    },
    4: {
        "tile": "Álcool",
        "name": "Álcool",
        "formula": "R–OH",
        "struct": "R–OH",
        "suffix": "…ol",
        "example": "Etanol",
        "detail": "A hidroxila se liga a um carbono saturado. Face 4 do dominó.",
    },
    5: {
        "tile": "Cetona",
        "name": "Cetona",
        "formula": "R–CO–R",
        "struct": "  O\n  ‖\nR–C–R",
        "suffix": "…ona",
        "example": "Propanona",
        "detail": "A carbonila fica entre dois carbonos. Face 5 do dominó.",
    },
    6: {
        "tile": "Aldeído",
        "name": "Aldeído",
        "formula": "R–CHO",
        "struct": "  O\n  ‖\nR–C–H",
        "suffix": "…al",
        "example": "Etanal",
        "detail": "A carbonila está na ponta da cadeia, ligada a hidrogênio. Face 6 do dominó.",
    },
}

RULES = [
    "O objetivo é ficar sem peças antes do oponente. Cada ponta do dominó é uma função oxigenada.",
    "Só encaixa função igual: álcool com álcool, cetona com cetona. A mesa tem duas pontas abertas.",
    "Sem encaixe, compre uma peça no cemitério. Se ele acabar e ainda não der para jogar, passe a vez.",
    "Se a mesa travar, vence quem ficou com a mão mais leve. Empate quando as duas mãos pesam igual.",
]
