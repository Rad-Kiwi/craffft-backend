import random

# Lists of first and last names
first_names = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth",
    "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Christopher", "Karen",
    "Charles", "Nancy", "Daniel", "Lisa", "Matthew", "Betty", "Anthony", "Helen", "Mark", "Sandra",
    "Donald", "Donna", "Steven", "Carol", "Paul", "Ruth", "Andrew", "Sharon", "Joshua", "Michelle",
    "Kenneth", "Laura", "Kevin", "Sarah", "Brian", "Kimberly", "George", "Deborah", "Timothy", "Dorothy",
    "Ronald", "Lisa", "Jason", "Nancy", "Edward", "Karen", "Jeffrey", "Betty", "Ryan", "Helen",
    "Jacob", "Sandra", "Gary", "Donna", "Nicholas", "Carol", "Eric", "Ruth", "Jonathan", "Sharon",
    "Stephen", "Michelle", "Larry", "Laura", "Justin", "Sarah", "Scott", "Kimberly", "Brandon", "Deborah",
    "Benjamin", "Dorothy", "Samuel", "Amy", "Gregory", "Angela", "Alexander", "Ashley", "Patrick", "Brenda",
    "Frank", "Emma", "Raymond", "Olivia", "Jack", "Cynthia", "Dennis", "Marie", "Jerry", "Janet",
    "Tyler", "Catherine", "Aaron", "Frances", "Jose", "Christine", "Henry", "Samantha", "Adam", "Debra",
    "Douglas", "Rachel", "Nathan", "Carolyn", "Peter", "Janet", "Zachary", "Virginia", "Kyle", "Maria",
    "Noah", "Heather", "Alan", "Diane", "Carl", "Julie", "Ralph", "Joyce", "Roger", "Victoria",
    "Bobby", "Kelly", "Wayne", "Christina", "Eugene", "Joan", "Louis", "Evelyn", "Philip", "Lauren",
    "Billy", "Judith", "Arthur", "Megan", "Bruce", "Cheryl", "Willie", "Andrea", "Jordan", "Hannah",
    "Ralph", "Jacqueline", "Roy", "Martha", "Eugene", "Gloria", "Louis", "Teresa", "Philip", "Sara",
    "Mason", "Janice", "Austin", "Marie", "Frederick", "Julia", "Albert", "Kathryn", "Wayne", "Frances",
    "Victor", "Alexis", "Harold", "Rebecca", "Kenneth", "Samantha", "Ralph", "Janet", "Arthur", "Catherine",
    "Eugene", "Frances", "Sean", "Christine", "Lawrence", "Deborah", "Christian", "Rachel", "Joe", "Carolyn",
    "Billy", "Janet", "Bruce", "Maria", "Willie", "Olivia", "Roy", "Heather", "Ralph", "Ruth"
]

last_names = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts",
    "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker", "Cruz", "Edwards", "Collins", "Reyes",
    "Stewart", "Morris", "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper",
    "Peterson", "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
    "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes",
    "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long", "Ross", "Foster", "Jimenez",
    "Powell", "Jenkins", "Perry", "Russell", "Sullivan", "Bell", "Coleman", "Butler", "Henderson", "Barnes",
    "Gonzales", "Fisher", "Vasquez", "Simmons", "Romero", "Jordan", "Patterson", "Alexander", "Hamilton", "Graham",
    "Reynolds", "Griffin", "Wallace", "Moreno", "West", "Cole", "Hayes", "Bryant", "Herrera", "Gibson",
    "Ellis", "Tran", "Medina", "Aguilar", "Stevens", "Murray", "Ford", "Castro", "Marshall", "Owens",
    "Harrison", "Fernandez", "McDonald", "Woods", "Washington", "Kennedy", "Wells", "Vargas", "Henry", "Chen",
    "Freeman", "Webb", "Tucker", "Guzman", "Burns", "Crawford", "Olson", "Simpson", "Porter", "Hunter",
    "Gordon", "Mendez", "Silva", "Shaw", "Snyder", "Mason", "Dixon", "Munoz", "Hunt", "Hicks",
    "Holmes", "Palmer", "Wagner", "Black", "Robertson", "Boyd", "Rose", "Stone", "Salazar", "Fox",
    "Warren", "Mills", "Meyer", "Rice", "Robertson", "Knight", "Cox", "Howard", "Ward", "Torres",
    "Peterson", "Graham", "Reynolds", "Powell", "Flores", "Hansen", "Hoffman", "Silva", "Woods", "Cole"
]

# Generate 1000 unique student names
student_names = []
used_combinations = set()

while len(student_names) < 1000:
    first = random.choice(first_names)
    last = random.choice(last_names)
    full_name = f"{first} {last}"
    
    # Ensure we don't have duplicates
    if full_name not in used_combinations:
        used_combinations.add(full_name)
        student_names.append(full_name)

# Create comma-separated string
student_names_string = ", ".join(student_names)

# Print the result
print("Here are 1000 student names as a comma-separated string:")
print("\n" + student_names_string)

# Also save to a file for easy copying
with open("student_names_1000.txt", "w") as f:
    f.write(student_names_string)

print(f"\n\nTotal names generated: {len(student_names)}")
print("Names also saved to 'student_names_1000.txt'")
