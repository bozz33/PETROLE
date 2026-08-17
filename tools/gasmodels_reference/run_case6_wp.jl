using GasModels
using Ipopt
using JSON
using JuMP
using SHA

const EXPECTED_GASMODELS_COMMIT = "21422f18e7e328732ec8edd7995446d33f58e789"
const CASE_RELATIVE_PATH = joinpath("test", "data", "matgas", "case-6-gf.m")
const UPSTREAM_OBJECTIVE_ATOL = 1.0e-6
const ACCEPTED_TERMINATION_STATUSES = Set([
    "LOCALLY_SOLVED",
    "ALMOST_LOCALLY_SOLVED",
    "OPTIMAL",
    "Suboptimal",
])

function sha256_file(path::String)::String
    return bytes2hex(SHA.sha256(read(path)))
end

function require_finite_float(value, label::String)::Float64
    number = Float64(value)
    isfinite(number) || error("$label doit être fini dans l'artefact de référence.")
    return number
end

function numeric_component_rows(
    solution::Dict,
    component_name::String,
    fields::Vector{Pair{String, String}},
)
    components = get(solution, component_name, Dict{String, Any}())
    rows = Vector{Dict{String, Any}}()

    for component_id in sort(collect(keys(components)))
        source = components[component_id]
        row = Dict{String, Any}("id" => component_id)
        for (source_field, artifact_field) in fields
            if haskey(source, source_field)
                row[artifact_field] = require_finite_float(
                    source[source_field],
                    "$component_name/$component_id/$source_field",
                )
            end
        end
        push!(rows, row)
    end

    return rows
end

function main()
    source_dir = abspath(get(ENV, "GASMODELS_SOURCE_DIR", "external/GasModels.jl"))
    output_dir = abspath(get(ENV, "PETROLE_REFERENCE_OUTPUT_DIR", "validation/gasmodels"))
    project_dir = abspath(@__DIR__)
    manifest_path = joinpath(project_dir, "Manifest.toml")
    project_path = joinpath(project_dir, "Project.toml")
    case_path = joinpath(source_dir, CASE_RELATIVE_PATH)

    isfile(case_path) || error("Cas GasModels introuvable : $case_path")
    isfile(manifest_path) || error("Manifest Julia absent : exécuter Pkg.instantiate avant le runner.")

    actual_commit = readchomp(`git -C $source_dir rev-parse HEAD`)
    actual_commit == EXPECTED_GASMODELS_COMMIT || error(
        "Commit GasModels inattendu : $actual_commit (attendu $EXPECTED_GASMODELS_COMMIT).",
    )
    string(Base.pkgversion(GasModels)) == "0.13.4" || error(
        "Version GasModels inattendue : $(Base.pkgversion(GasModels)).",
    )

    parsed_case = GasModels.parse_file(case_path)
    optimizer = JuMP.optimizer_with_attributes(
        Ipopt.Optimizer,
        "print_level" => 0,
        "sb" => "yes",
    )
    result = GasModels.solve_gf(case_path, GasModels.WPGasModel, optimizer)

    termination_status = string(result["termination_status"])
    objective = require_finite_float(result["objective"], "objective")
    solution = result["solution"]

    artifact = Dict{String, Any}(
        "schema_version" => "petrole-gasmodels-reference-v2",
        "reference_only" => true,
        "certification_claim" => false,
        "solver" => Dict(
            "name" => "GasModels.jl",
            "version" => string(Base.pkgversion(GasModels)),
            "git_commit" => actual_commit,
            "formulation" => "WPGasModel",
            "problem" => "solve_gf",
            "optimizer" => "Ipopt",
            "optimizer_version" => string(Base.pkgversion(Ipopt)),
            "julia_version" => string(VERSION),
            "manifest_sha256" => sha256_file(manifest_path),
            "project_sha256" => sha256_file(project_path),
        ),
        "case" => Dict(
            "name" => "case-6-gf.m",
            "relative_path" => CASE_RELATIVE_PATH,
            "input_sha256" => sha256_file(case_path),
            "units_declared" => get(parsed_case, "units", nothing),
            "is_per_unit_input" => get(parsed_case, "per_unit", get(parsed_case, "is_per_unit", nothing)),
            "base_pressure" => get(parsed_case, "base_pressure", nothing),
            "base_length" => get(parsed_case, "base_length", nothing),
            "base_flow" => get(parsed_case, "base_flow", nothing),
            "base_density" => get(parsed_case, "base_density", nothing),
            "sound_speed" => get(parsed_case, "sound_speed", nothing),
            "temperature" => get(parsed_case, "temperature", nothing),
            "compressibility_factor" => get(parsed_case, "compressibility_factor", nothing),
            "gas_specific_gravity" => get(parsed_case, "gas_specific_gravity", nothing),
        ),
        "upstream_test_criteria" => Dict(
            "source_ref" => "GasModels.jl/test/gf.jl@$EXPECTED_GASMODELS_COMMIT",
            "compressor_ratio_check_ref" => "GasModels.jl/test/common.jl@$EXPECTED_GASMODELS_COMMIT",
            "accepted_termination_statuses" => sort(collect(ACCEPTED_TERMINATION_STATUSES)),
            "objective_target" => 0.0,
            "objective_absolute_tolerance" => UPSTREAM_OBJECTIVE_ATOL,
            "petrole_benchmark_tolerance" => nothing,
        ),
        "result" => Dict(
            "termination_status" => termination_status,
            "objective" => objective,
            "solve_time_s" => get(result, "solve_time", nothing),
            "junction" => numeric_component_rows(solution, "junction", ["p" => "p_pu"]),
            "pipe" => numeric_component_rows(solution, "pipe", ["f" => "f_pu"]),
            "compressor" => numeric_component_rows(
                solution,
                "compressor",
                ["f" => "f_pu", "r" => "ratio"],
            ),
            "delivery" => numeric_component_rows(solution, "delivery", ["fd" => "fd_pu"]),
            "receipt" => numeric_component_rows(solution, "receipt", ["fg" => "fg_pu"]),
            "transfer" => numeric_component_rows(solution, "transfer", ["ft" => "ft_pu"]),
        ),
        "provenance" => Dict(
            "gasmodels_repository" => "lanl-ansi/GasModels.jl",
            "gasmodels_case_ref" => "test/data/matgas/case-6-gf.m@$EXPECTED_GASMODELS_COMMIT",
            "petrole_runner_ref" => "tools/gasmodels_reference/run_case6_wp.jl",
            "network_state_values_are_per_unit" => true,
            "compressor_ratio_is_dimensionless" => true,
            "si_conversion_performed_by_runner" => false,
        ),
    )

    mkpath(output_dir)
    output_path = joinpath(output_dir, "case-6-gf-wp-reference.json")
    open(output_path, "w") do io
        JSON.print(io, artifact, 2)
        write(io, '\n')
    end

    println("Référence GasModels écrite : $output_path")
    println("input_sha256=", artifact["case"]["input_sha256"])
    println("output_sha256=$(sha256_file(output_path))")
    println("termination_status=$termination_status")
    println("objective=$objective")

    termination_status in ACCEPTED_TERMINATION_STATUSES || error(
        "Statut GasModels hors des statuts acceptés par son test upstream : $termination_status",
    )
    abs(objective) <= UPSTREAM_OBJECTIVE_ATOL || error(
        "Objectif GasModels hors du contrôle upstream : |$objective| > $UPSTREAM_OBJECTIVE_ATOL",
    )
end

main()
