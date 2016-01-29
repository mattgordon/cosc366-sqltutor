
class ArffWriter():
    def __init__(self, filename, relation_name):
        self.attributes = []
        self.comments = []
        self.relation_name = relation_name
        self.file = open(filename, mode='w')
    
    def write(self):
        self.file.write('@relation ' + self.relation_name + '\n\n')
        for attr in self.attributes:
            # write out attribute metadata
            self.file.write('@attribute ' + attr.name + ' ' + attr.type + '\n')
        self.file.write('\n@data\n')
        for i in range(len(self.attributes[0].values)):
            for comment in filter(lambda c: c.index == i, self.comments):
                self.file.write('% ' + comment.comment + '\n')
            self.file.write(','.join(map(lambda v: '?' if v == 'None' else v,
                                    [str(a.values[i]) for a in self.attributes]
                                    )) 
                            + '\n')
        self.file.close()

class ArffAttribute():
    def __init__(self, name, type, values):
        self.name = name
        self.type = type
        self.values = values
    
class ArffDataComment():
    def __init__(self, index, comment):
        self.index = index
        self.comment = comment
        
