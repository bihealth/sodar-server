"""Rules for the ontologyaccess app"""

import rules


# Predicates -------------------------------------------------------------


# None needed right now


# Rules ------------------------------------------------------------------


# Rules should not be needed, use permissions for user rights


# Permissions ------------------------------------------------------------


# Allow viewing ontology list
rules.add_perm('ontologyaccess.view_list', rules.is_superuser)

# Allow viewing details of an ontology
rules.add_perm('ontologyaccess.view_ontology', rules.is_superuser)

# Allow querying for terms in an ontology
rules.add_perm('ontologyaccess.query_ontology', rules.is_authenticated)

# Allow creation of ontologies
rules.add_perm('ontologyaccess.create_ontology', rules.is_superuser)

# Allow updating ontologies
rules.add_perm('ontologyaccess.update_ontology', rules.is_superuser)

# Allow deletion of ontologies
rules.add_perm('ontologyaccess.delete_ontology', rules.is_superuser)
